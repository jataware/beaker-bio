# -*- coding: utf-8 -*-
import json
import logging
import inspect
from archytas.react import ReActAgent
from archytas.tool_utils import tool, toolset, AgentRef, LoopControllerRef
from typing import Any, Dict
import importlib
import io
import contextlib
logger = logging.getLogger(__name__)
from setup_context.example_handling.utils import check_python_code
import logging
import json
import importlib
import pkgutil
import re

@toolset()
class Toolset:
    """Toolset for our context"""

    @tool(autosummarize=True)
    async def get_available_functions(self, package_name: str, agent: AgentRef):
        """
        Querying against the module or package should list all available submodules and functions that exist, so you can use this to discover available
        functions and the query the function to get usage information.
        You should ALWAYS try to run this on specific submodules, not entire libraries. For example, instead of running this on `mira` you should
        run this function on `mira.modeling`. In fact, there should almost always be a `.` in the `package_name` argument.
        
        This function should be used to discover the available functions in the target library or module and get an object containing their docstrings so you can figure out how to use them.

        This function will return an object and store it into self.__functions. The object will be a dictionary with the following structure:
        {
            function_name: <function docstring>,
            ...
        }

        Read the docstrings to learn how to use the functions and which arguments they take.

        Args:
            package_name (str): this is the name of the package to get information about. For example "mira.modeling"   
        """
        functions = {}
        module=importlib.import_module(package_name)
        info_response = await self.get_docstrings(module)
     
        for var_name, info in info_response.items():
            if var_name in functions:
                functions[var_name] = info
            else:
                functions[var_name] = info

        agent.functions.update(functions)

        return functions   
    
    async def get_docstrings(self,module):
        result = {}
        prefix = module.__name__ + "."

        for importer, modname, ispkg in pkgutil.walk_packages(module.__path__, prefix):
            try:
                # Load the submodule
                submodule = importlib.import_module(modname)
                # Process the submodule
                for attribute_name in dir(submodule):
                    if attribute_name.startswith('_'):
                        continue

                    attribute = getattr(submodule, attribute_name)
                    full_name = f"{modname}.{attribute_name}"

                    if hasattr(attribute, '__doc__'):
                            if attribute.__doc__:
                                result[full_name] = attribute.__doc__
            except Exception as e:
                # Skip modules that can't be imported
                continue

        return result

    @tool(autosummarize=True)
    async def get_functions_and_classes_docstring(self, list_of_function_or_class_names: list, agent: AgentRef):
        """
        Use this tool to additional information on individual function or class such as their inputs, outputs and description (and generally anything else that would be in a docstring)
        You should ALWAYS use this tool before writing or checking code to check the function signatures of the functions or classes you are about to use.
        
        Read the information returned to learn how to use the function or class and which arguments they take.
        
        The function and class names used in the input to this tool should include the entire module hierarchy, ie. mira.modeling.triples.Triple
        
        Args:
            list_of_function_or_class_names (list): this is a list of the the names of the functions and/or classes to get information about. For example ["mira.modeling.triples.Triple","mira.metamodel.io.model_from_json_file"]   
        """
        #TODO: figure out cause of this and remove ugly filter
        if type(list_of_function_or_class_names)==dict:
            list_of_function_or_class_names=list_of_function_or_class_names['list_of_function_or_class_names']
        help_string=''
        for func_or_class_name in list_of_function_or_class_names:
            module_name=func_or_class_name.rsplit('.', 1)[0]
            importlib.import_module(module_name)
    
            with io.StringIO() as buf, contextlib.redirect_stdout(buf):
                help(func_or_class_name)
                # Store the help text in the dictionary
                help_text = buf.getvalue()
            help_string+=f'{func_or_class_name}: {help_text}'
            agent.functions[func_or_class_name]=help_text
        return help_string
    
    @tool(autosummarize=True)
    async def get_functions_and_classes_source_code(self, list_of_function_or_class_names: list, agent: AgentRef):
        """
        Use this tool to additional information on individual function or class such as their inputs, outputs and description (and generally anything else that would be in a docstring)
        You should ALWAYS use this tool before writing or checking code to check the function signatures of the functions or classes you are about to use.
        
        Read the information returned to learn how to use the function or class and which arguments they take.
        
        The function and class names used in the input to this tool should include the entire module hierarchy, ie. mira.modeling.triples.Triple
        
        Args:
            list_of_function_or_class_names (list): this is a list of the the names of the functions and/or classes to get information about. For example ["mira.modeling.triples.Triple","mira.metamodel.io.model_from_json_file"]   
        """
        #TODO: figure out cause of this and remove ugly filter
        if type(list_of_function_or_class_names)==dict:
            list_of_function_or_class_names=list_of_function_or_class_names['list_of_function_or_class_names']
        help_string=''
        for func_or_class_name in list_of_function_or_class_names:
            module_path, object_name = func_or_class_name.rsplit('.', 1)
            module=importlib.import_module(module_path)
            obj = getattr(module, object_name)
            try:
                source_code=inspect.getsource(obj)
            except TypeError:
                source_code=inspect.getsource(module)
            #TODO: maybe use help on the object if it is an object and not a class?
            help_string+=f'{func_or_class_name} source code: \n{source_code}'
            agent.functions[func_or_class_name]=help_string
        return help_string
    
    @tool(autosummarize=True)
    async def search_documentation(self, query: str):
        """
        Use this tool to search the documentation for sections relevant to the task you are trying to perform.
        Input should be a natural language query meant to find information in the documentation as if you were searching on a search bar.
        Response will be sections of the documentation that are relevant to your query.
        
        Args:
            query (str): Natural language query. Some Examples - "ode model", "sir model", "using dkg package"
        """
        from src.beaker_bio_context.procedures.python3.embed_documents import query_docs
        return query_docs(query,path="./chromadb_functions")
    
    @tool(autosummarize=True)
    async def search_functions_classes(self, query: str):
        """
        Use this tool to search the code in the mira repo for function and classes relevant to your query.
        Input should be a natural language query meant to find information in the documentation as if you were searching on a search bar.
        Response will be a string with the top few results, each result will have the function or class doc string and the source code (which includes the function signature)
        
        Args:
            query (str): Natural language query. Some Examples - "ode model", "sir model", "using dkg package"
        """
        from src.beaker_bio_context.procedures.python3.embed_functions_classes_2 import query_functions_classes
        return query_functions_classes(query,path="./chromadb_functions") 


class ProxyAgent(ReActAgent):
    #ProxyAgent(Toolset)


    def __init__(
        self,
        config: Dict[str, Any],
        tools: list = [Toolset],
        use_few_shot=False,
        **kwargs,
    ):

        super().__init__(
            tools=tools,
            verbose=True,
            max_errors=5,
            spinner=None,
            rich_print=False,
            allow_ask_user=False,
            thought_handler=None, #print?
            **kwargs
        )
        with open('context.json','r') as f:
            self.context_conf = json.loads(f.read())
        self.library_name=self.context_conf.get("library_names","a Jupyter notebook")[0]
        self.library_description=self.context_conf.get("library_descriptions",'')[0]
        self.sub_module_description=self.context_conf.get('library_submodule_descriptions', '')[0]
        self.variables={}
        self.imported_modules={}
        self.functions={}
        self.use_few_shot=use_few_shot
        self.few_shot_examples=''
        self.set_auto_context("Default context", self.auto_context)
        self.most_recent_user_query=''
        
    def get_info(self):
        """
        """
        info = {
            "name": self.__class__.__name__,
            "tools": {tool_name: tool_func.__doc__.strip() for tool_name, tool_func in self.tools.items()},
            "agent_prompt": self.__class__.__doc__.strip(),
        }
        return info
    def get_code (self, name, render_dict: Dict[str, Any]=None) -> str:       
        if render_dict is None:
                render_dict = {}
        template = self.templates.get(name, None)
        if template is None:
            raise ValueError(
                f"'{name}' is not a defined procedure for context '{self.__class__.__name__}' and "
                f"subkernel '{self.subkernel.DISPLAY_NAME} ({self.subkernel.KERNEL_NAME})'"
            )
        return template.render(**render_dict)

    async def auto_context(self):
        from src.beaker_bio_context.procedures.python3.dynamic_example_selector import query_examples 
        most_recent_user_query=''
        for message in self.messages:
            if message['role']=='user':
                most_recent_user_query=message['content']
        if most_recent_user_query!=self.most_recent_user_query:
            self.most_recent_user_query = most_recent_user_query
            if self.use_few_shot:
                self.few_shot_examples=query_examples(most_recent_user_query,path="./chromadb_functions")
        
        intro_few_shot=f"""You are an exceptionally intelligent coding assistant that consistently delivers accurate and reliable responses to user instructions.
    {self.library_description}
    
    You should ALWAYS try looking up the what the user is asking you to do or portions of what the user is asking you to do in the documentation to get a sense of how it can be done.
    You should ALWAYS think about which functions and classes from {self.library_name} you are going to use before you write code. Try to use {self.library_name} as much as possible.
    You can do so in the following ways: 
    If the functions you want to use are in the context below, no need to look them up again.
    Otherwise, first try to use the Toolset.search_functions_classes to search for relevant functions and classes.
    If that does not provide enough information, lookup the available functions for related modules using Toolset.get_available_functions.
    If there is a main class or function you are using, you can lookup all the information on it and all the objects and functions required to use it using Toolset.get_class_or_function_full_information.
    Use this when you want to instantiate a complicated object.
    
    You can lookup source code for individual functions or classes using the Toolset.get_functions_and_classes_source_code before using a function from {self.library_name}.
    
    Below is some information on the submodules in {self.library_name}:
    
    {self.sub_module_description}
            
    Additionally here are some similar examples of similar user requests and your previous successful code generations in the format [[Request,Code]].
    If the request from the user is similar enough to one of these examples, use it to help write code to answer the user's request.
        
    {self.few_shot_examples}
    """ #use for established lib testing..
        intro_no_few_shot=f"""You are an exceptionally intelligent coding assistant that consistently delivers accurate and reliable responses to user instructions.
    {self.library_description}
    
    You should ALWAYS try looking up the what the user is asking you to do or portions of what the user is asking you to do in the documentation to get a sense of how it can be done.
    You should ALWAYS think about which functions and classes from {self.library_name} you are going to use before you write code. Try to use {self.library_name} as much as possible.
    You can do so in the following ways: 
    If the functions you want to use are in the context below, no need to look them up again.
    Otherwise, first try to use the Toolset.search_functions_classes to search for relevant functions and classes.
    If that does not provide enough information, lookup the available functions for related modules using Toolset.get_available_functions.
    If there is a main class or function you are using, you can lookup all the information on it and all the objects and functions required to use it using Toolset.get_class_or_function_full_information.
    Use this when you want to instantiate a complicated object.
    
    You can lookup source code for individual functions or classes using the Toolset.get_functions_and_classes_source_code before using a function from {self.library_name}.
    
    Below is some information on the submodules in {self.library_name}:
    
    {self.sub_module_description}
    """ #use for bottom up test
        
        code_environment2=f"""These are the variables in the user's current code environment with key value pairs:
{self.variables}

The user has also imported the following modules: {','.join(self.imported_modules)}. So you don't need to import them when generating code.
When writing code that edits the variables that the user has in their environment be sure to modify them in place. 
For example if we have a variable a=1, if we wanted to change a to 2, we you write a=2.
When the user asks you to perform an action, if they specifically mention a variable name, be sure to use that variable.
Additionally if the object they ask you to update is similar to an object in the code environment, be sure to use that variable. 
"""
        outro = f"""
        Please answer any user queries or perform user instructions to the best of your ability, but do not guess if you are not sure of an answer.
        """
        intro=intro_few_shot if self.use_few_shot else intro_no_few_shot
        result = "\n".join([intro,code_environment2,outro])
        return result
    
    @tool()
    async def ask_user(
        self, query: str, agent: AgentRef, loop: LoopControllerRef,
    ) -> str:
        """
        Sends a query to the user and returns their response

        Args:
            query (str): A fully grammatically correct question for the user.

        Returns:
            str: The user's response to the query.
        """
        #asks an llm user to answer the question..
        from setup_context.llm_utils import ask_gpt #may need to be async?
        answer_llm_query="""You have submitted a request to the mira agent, whose purpose is to help you use the {library_name} library. 
        {library_description}. Your request was : {request}. 
        In order to complete your request, the agent has a question. 
        Please answer the question in json format similar to the following: {{"answer":your_answer}}. 
        Here is the question : {question}.
        """
        #TODO: this may break in conversation, might only work for first request, give whole conv history to agent?
        res=ask_gpt(answer_llm_query.format(library_name=self.library_name,
                                            library_description=self.library_description,
                                            request=self.most_recent_user_query,question=query),
                    model='gpt-4-0125-preview')
        try:
            user_answer=json.loads(res)
            user_answer=user_answer['answer']
        except:
            user_answer='There was an issues with the user answering this question, please proceed with your best guess on what the user would want'
        return user_answer
        

    @tool()
    async def submit_code(self, code: str, agent: AgentRef, loop: LoopControllerRef) -> None:
        """
        Use this when you are ready to submit your code to the user. If the user asks for code, you should use this tool as your final action.
        
        
        Ensure to handle any required dependencies, and provide a well-documented and efficient solution. Feel free to create helper functions or classes if needed.
        
        Please generate the code as if you were programming inside a Jupyter Notebook and the code is to be executed inside a cell.
        You MUST wrap the code with a line containing three backticks before and after the generated code like the code below but replace the "triple_backticks":
        ```
        import numpy
        ```

        No additional text is needed in the response, just the code block with the triple backticks.

        Args:
            code (str): python code block to be submitted to the user inside triple backticks.
        """        
        loop.set_state(loop.STOP_SUCCESS)
        preamble, code, coda = re.split("```\w*", code)
        # self.tools['']
        # result = json.dumps(
        #     {
        #         "action": "code_cell",
        #         "language": "python3",
        #         "content": code.strip(),
        #     }
        # )

        return f'ProxyAgent.SubmitCode: {code.strip()}'

def example_use():
    from setup_context.example_handling.beaker_agent_proxy.proxy_agent import ProxyAgent
    import json
    agent=ProxyAgent(json.load(open('/media/ssd/recovered_files/beaker-bio/context.json','r')))
    res=agent.react('ask me what my name is') 
