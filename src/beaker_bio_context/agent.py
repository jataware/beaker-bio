import json
import logging
import re
from typing import Optional

import pandas

from archytas.react import Undefined
from archytas.tool_utils import AgentRef, LoopControllerRef, is_tool, tool, toolset

from beaker_kernel.lib.agent import BaseAgent
from beaker_kernel.lib.context import BaseContext
from .CodeLATS.code_lats import use_lats
logger = logging.getLogger(__name__)
from archytas.tools import PythonTool
from .new_base_agent import NewBaseAgent
import importlib
import io
import sys
import contextlib
import traceback
import inspect
from pydantic import BaseModel
from typing import get_args, get_origin
from typing import Annotated,Union,List

#TODO: improve notebook representation/knowledge that the agent has..
    #TODO: add descriptions to code env objects being passed around in a generic way..
    #TODO: variables include some extra background crap sometimes
#TODO: what we really need is all of the classes and their arguments and how they interact and gpt-4 should be able to do soemthing with that..
    #TODO: we need a way of understanding the class structure, and maybe the code structure. Maybe we can make a directed graph like David was trying to..
#TODO: add lookup examples??
#TODO: convert MUST and ALWAYS to enforcable or directed flow
#TODO: add knowledge of state of notebook to context keys - _ih, _oh (in and out full lists) (look at langchain version..)
#TODO: add custom within react loop summarization.. save to variable then put in autocontext? Maybe a dialog where I ask the agent which of these is useful to save then only save those?
#TODO: try docstring enforcement - ie they must put in the correct variables.. (think this is true now just the mira errors are more nefarious)
#TODO: try using gpt 3.5 for some things..
#TODO: rewrite files in easyTool format using gpt-3.5..
#DONE: try examples from darpa-askem beaker mira examples..

#TODO: add list of state variables that were instantiated to few shot example search?

#TODO: add function sigs to info return and skill return
#TODO: hybrid or keyword search??
#TODO: add few shot examples of actual flow (ie conversations)
#TODO: actual codelats or code completion chains with self reflection..

# @tool()
# def python_repl(code: str, agent: AgentRef) -> str:
#         """
#         Tool which can be used to run python code. Use this to check correctness of your code before you submit it to the user.
#         Runs python code in a python environment.
        
#         The initial setup of the environment will be a copy of the user's environment, including instantiated variables and imported modules.
#         The environment is not persistent between runs, so any variables created will not be available in subsequent runs.
#         The only visible effects of this tool are from output to stdout/stderr. If you want to view a result, you MUST print it.
#         Remember, if you are confused in any way about how to use a library, make sure to call `help(module_name)` to learn as much as you can.
        
#         Args:
#             code (str): The code to run
        
#         Returns:
#             str: The stdout output and standard error of the code
#         """
#         repl_locals=agent.context.variables
#         repl_modules=agent.context.imported_modules
#         captured_stdout = io.StringIO()
#         captured_stderr = io.StringIO()
#         sys.stdout = captured_stdout
#         sys.stderr = captured_stderr
#         code='\n'.join([f'import {module}' for module in repl_modules])+'\n'+code
#         try:
#             exec(code, repl_locals)
#         except Exception as e:
#             sys.stderr.write(str(e))
            
#         # restore stdout/stderr
#         sys.stdout = sys.__stdout__
#         sys.stderr = sys.__stderr__
        
#         return captured_stdout.getvalue(), captured_stderr.getvalue()


@toolset()
class MiraToolset:
    """Toolset for Mira context"""
#    @tool(autosummarize=True)
#    async def generate_code_using_lats(self, query: str, agent: AgentRef) -> None:
#        use_lats(query,model='gpt-3.5-turbo-1106',tree_depth=2)#'gpt-4-1106-preview''gpt-4-1106-preview'

    #generate_code.__doc__

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
        code = agent.context.get_code("info", {"package_name": package_name})
        info_response = await agent.context.beaker_kernel.evaluate(
            code,
            parent_header={},
        )
        with open('/tmp/info.json', 'r') as f:
            info = json.loads(f.read())        
        for var_name, info in info.items():
            if var_name in functions:
                functions[var_name] = info
            else:
                functions[var_name] = info

        agent.context.functions.update(functions)

        return functions
    
    # @tool(autosummarize=True)
    # async def get_class_or_function_full_information(self,class_or_function_name:str):
    #     """ This tool will get function signatures and doc strings for all the classes and function names which are required to use the input class or function.
    #     For example if you had a class module.class1 which took as inputs either class2,class3 or class 4, This function would return information for class 1,2,3 and 4.
    #     Input to this tool should be the class or function name with the complete module hierarchy ie. mira.modeling.triples.Triple
    #     Note that this can also be used on class methods like mira.metamodel.template_model.TemplateModel.get_parameters_from_rate_law to get more information on how to use them.
        
    #     Args:
    #         class_or_function_name (str): this is a string with the class or function name with full module hierarchy For example ["mira.modeling.triples.Triple","mira.metamodel.io.model_from_json_file"] 
    #     """
    #     def get_class_information(cls):
    #         function_information=[]
    #         for name, method in inspect.getmembers(cls, inspect.isfunction):
    #            function_information.append(get_function_information(method))
    #         return function_information
    #     def get_function_information(func):
    #         signature = inspect.signature(func)
    #         docstring = func.__doc__ or ''
    #         return signature,docstring
        
    #     #works for pydantic with annotated[union] at least..
    #     def analyze_class_initialization(cls):
    #         # Check if the class is a Pydantic model
    #         lookup_classes_functions=[]
    #         if issubclass(cls, BaseModel):
    #             for field_name in cls.__fields__.keys():
    #                 field=cls.__fields__[field_name]
    #                 if get_origin(field.type_) == Annotated:
    #                     actual_type = get_args(field.type_)[0]
    #                     if get_origin(actual_type) == Union:
    #                         actual_type = get_args(actual_type)
    #                 elif get_origin(actual_type) == Union:
    #                     actual_type = get_args(field.type_)[0]
    #                 else:
    #                     actual_type = field.type_
    #                 if type(actual_type) ==tuple or type(actual_type) ==list:
    #                     for field_type in actual_type:
    #                         lookup_classes_functions.append(field_type)
    #                 else:
    #                     lookup_classes_functions.append(actual_type)
    #             return lookup_classes_functions
    #         else:
    #             # Handle regular classes with an __init__ method
    #             if '__init__' in dir(cls):
    #                 init_signature = inspect.signature(cls.__init__)
    #                 for param_name, param in init_signature.parameters.items():
    #                     if param_name != 'self':  # Exclude 'self' from the parameters list
    #                         if param.annotation != inspect.Parameter.empty:
    #                             lookup_classes_functions.append(param_name)
    #                 return lookup_classes_functions
    #             else:
    #                 return None
        #TODO: needs work, need to get if type is a class or somethign complicated, str for example is self explanatory
        
        # def analyze_function_requirements(func):
        #     signature = inspect.signature(func)
        #     params_to_lookup=[]
        #     for name, param in signature.parameters.items():
        #         if param.annotation is not inspect.Parameter.empty and param.default is not inspect.Parameter.empty:
        #             params_to_lookup.append(name) #do we actually want param here?
        #     return params_to_lookup
        #     # if signature.return_annotation is not inspect.Parameter.empty:
        #     #     print(f"Returns: {signature.return_annotation}")
                
        # #get class or function information 
        # module_path, object_name = class_or_function_name.rsplit('.', 1)
        # module = importlib.import_module(module_path)
        # main_obj = getattr(module, object_name)
        # doc_string=main_obj.__doc__ or ''
        # if inspect.isclass(main_obj):
        #     signature=f'class {main_obj.__name__}:'
        # else:
        #     signature = inspect.signature(main_obj)
        # try:
        #     source_code=inspect.getsource(main_obj)
        # except TypeError:
        #     source_code=inspect.getsource(module)
        # #if class get method signatures and doc strings
        # main_obj_method_information={}
        # if inspect.isclass(main_obj):
        #     for name, obj in inspect.getmembers(module):
        #         if inspect.isclass(obj):
        #             main_obj_method_information[name]=get_class_information(obj)
        #         elif inspect.isfunction(obj):
        #             main_obj_method_information[name]=get_function_information(obj)
        # #if class get the information required to instantiate the class
        # if inspect.isclass(main_obj):
        #     required_lookups=analyze_class_initialization(main_obj)
        # #if function get the information on the function inputs
        # if inspect.isfunction(main_obj):
        #     required_lookups=analyze_function_requirements(main_obj)
        # required_sources={str(lookup):inspect.getsource(lookup) for lookup in required_lookups}
        # print_out=f'Here is the information on {class_or_function_name} and the objects and functions required to instantiate it.'
        # print_out+=f'{class_or_function_name} signature : {signature}\n{class_or_function_name} doc_string : {doc_string}\n'
        # for key in required_sources.keys():
        #     print_out+=f'Source Code for {key}:\n{required_sources[key]}\n'
        # return print_out
            
    
    
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
        print(list_of_function_or_class_names)
        for func_or_class_name in list_of_function_or_class_names:
            module_name=func_or_class_name.rsplit('.', 1)[0]
            importlib.import_module(module_name)
    
            with io.StringIO() as buf, contextlib.redirect_stdout(buf):
                help(func_or_class_name)
                # Store the help text in the dictionary
                help_text = buf.getvalue()
            help_string+=f'{func_or_class_name}: {help_text}'
            agent.context.functions[func_or_class_name]=help_text
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
            #agent.context.functions[func_or_class_name]=help_text
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
        from .procedures.python3.embed_documents import query_docs
        return query_docs(query)
    
    @tool(autosummarize=True)
    async def search_functions_classes(self, query: str):
        """
        Use this tool to search the code in the mira repo for function and classes relevant to your query.
        Input should be a natural language query meant to find information in the documentation as if you were searching on a search bar.
        Response will be a string with the top few results, each result will have the function or class doc string and the source code (which includes the function signature)
        
        Args:
            query (str): Natural language query. Some Examples - "ode model", "sir model", "using dkg package"
        """
        from .procedures.python3.embed_functions_classes_2 import query_functions_classes
        return query_functions_classes(query)

    #get_available_functions.__doc__

    #TODO: not really working for ODEs.. not sure it works well in general...
    #TODO: change to multiple queries?
    # @tool(autosummarize=True)
    # async def skill_search(self, query: str, agent: AgentRef) -> None:
    #     """
    #     This function should be used to search for available classes, functions and methods that are available and relevant to the task described in the `query`.

    #     The query should be simple and specific and not overly verbose in order to yield the most relevant results.

    #     This function will return a search result object of the form:

    #     ```
    #     {'function_or_class_name': {
    #                     'description': 'description of the function here',
    #                     'docstring': 'the docstring of the function here',
    #                     'source_code': 'the source code of the function here',
    #                     },
    #     ...
    #     }
    #     ```

    #     You should then read the docstrings and the source code to learn how to use the functions/classes/etc and which arguments they take and methods they have.

    #     Args:
    #         query (str): this is the query that describes the task against which you wish to find matching functions. This should be simple and specific."
    #     """
    #     from .procedures.python3.query_functions import query_functions
    #     return query_functions(query)


class MiraAgent(NewBaseAgent):
    """
    You are assisting us in performing important scientific tasks.

    If you don't have the details necessary, you should use the ask_user tool to ask the user for them.
    """

    def __init__(self, context: BaseContext = None, tools: list = None, **kwargs):
        tools = [MiraToolset]
        super().__init__(context, tools, **kwargs)
        with open('context.json', 'r') as f:
            self.context_conf = json.load(f)
        self.most_recent_user_query=''
        self.checked_code=False
        self.code_attempts=0
            
# Here is an example of a code block to be submitted - 
# ```
# from mira.sources.biomodels import get_template_model
# template_model = get_template_model('BIOMD0000000956')
# ```  
#to over-ride to make things happen before react loop (ie few shot dynamic examples..)
   # async def react_async(self, query: str) -> str:
   #     result = await super().react_async(query)
   #     self.do_something()
   #     return result
   
    # @tool()
    # async def python_repl(self,code:str):
    #     """
    #     Tool which can be used to run python code. Use this to check correctness of your code before you submit it to the user.
    #     Runs python code in a python environment. Code submitted to this tool should not include backticks before and after the code. 
    #     Just simply submit the code.
        
    #     The initial setup of the environment will be a copy of the user's environment, including instantiated variables and imported modules.
        
    #     The environment is not persistent between runs, so any variables created will not be available in subsequent runs. 
    #     However, any time the user runs code in their environment, this environment will be synced to theirs.
    #     So when you use submit_code you can assume the user is likely to run the code you submit and this code env will sync to that one.
    #     The only visible effects of this tool are from output to stdout/stderr. If you want to view a result, you MUST print it.
    #     Remember, if you are confused in any way about how to use a library, make sure to call `help(module_name)` to learn as much as you can.
        
    #     Args:
    #         code (str): The code to run
        
    #     """
    #     repl_locals=self.context.variables
    #     self.debug(event_type="code",content={
    #                 "variables": repl_locals,
    #             })
    #     repl_modules=self.context.imported_modules
    #     self.debug(event_type="code",content={
    #                 "imported_modules": repl_modules,
    #             })
    #     captured_stdout = io.StringIO()
    #     captured_stderr = io.StringIO()
    #     sys.stdout = captured_stdout
    #     sys.stderr = captured_stderr
    #     code = '\n'.join([f'import {module}' for module in repl_modules]) +'\n' + code

    #     # code='\n'.join([f'import {module}' for module in repl_modules])+'\n'+\
    #     #     """for variable in repl_modules:\n    exec(f"{variable}={repl_modules[variable]}")"""+code
    #     traceback_str=''
    #     print_out='\n'
    #     try:
    #         exec(code, repl_locals)
    #         self.checked_code=True
    #         self.code_attempts=0
    #         # self.debug(event_type="code",content={
    #         #             "checked_code": self.checked_code,
    #         #         })
    #     except Exception as e:
    #         traceback_str = traceback.format_exc()
    #         sys.stderr.write(str(e))
    #         print_out='''End of Traceback.\n It seems like the code you attempted to run was unsuccessful. 
    #         If you are having difficulty with a particular function(s) or class(es) look up their source code using the MiraToolset.get_functions_and_classes_source_code tool please'''
    #         self.checked_code=False
    #         self.code_attempts+=1
    #         if self.code_attempts>=2:
    #             print_out='You have already attempted to run code unsucessfully twice. Please let the user know the issues you are having and include your attempted code in your final_answer.' 
          
    #     # restore stdout/stderr
    #     sys.stdout = sys.__stdout__
    #     sys.stderr = sys.__stderr__
    #     std_out,std_err=captured_stdout.getvalue(), captured_stderr.getvalue()
    #     self.debug(event_type="code",content={
    #                 "stdout": std_out,
    #                 "stderr": traceback_str,
    #             })
    #     #TODO: update variables in autocontext or nah?
    #     return f'Stdout:{std_out}\n\n Std_error with traceback : {traceback_str}\n{print_out}'#, print_out
  
    # #If you try to use this tool before successful running the code in the MiraAgent.python_repl tool, you will receieve a response letting you know you must check your code.
    # #If you attempted to run your code but it did not run successfully you will not be able to run this code.
    # @tool()
    # async def submit_code(self, code: str, agent: AgentRef, loop: LoopControllerRef) -> None:
    #     """
    #     Use this after you have checked your code using the MiraAgent.python_repl tool and are ready to submit your code to the user.
    #     If you try to use this tool before successful running the code in the MiraAgent.python_repl tool, you will receieve a response letting you know you must check your code.
    #     If you attempted to run your code but it did not run successfully you will not be able to run this code.
        
    #     Ensure to handle any required dependencies, and provide a well-documented and efficient solution. Feel free to create helper functions or classes if needed.
        
    #     Please generate the code as if you were programming inside a Jupyter Notebook and the code is to be executed inside a cell.
    #     You MUST wrap the code with a line containing three backticks before and after the generated code like the code below but replace the 'triple_backticks':
    #     ```
    #     import mira
    #     ```

    #     No additional text is needed in the response, just the code block with the triple backticks.
        

    #     Args:
    #         code (str): python code block to be submitted to the user inside triple backticks.
    #     """
    #     if self.checked_code:
    #         loop.set_state(loop.STOP_SUCCESS)
    #         preamble, code, coda = re.split("```\w*", code)
    #         result = json.dumps(
    #             {
    #                 "action": "code_cell",
    #                 "language": "python3",
    #                 "content": code.strip(),
    #             }
    #         )
    #         #check if successful then reset check code...
    #         self.checked_code=False
    #         return result
    #     else:
    #         if self.code_attempts>=2:
    #             self.code_attempts=0
    #             return 'You have already attempted to run code unsucessfully twice. Please let the user know the issues you are having and include your attempted code in your final_answer.'    
    #         else:
    #             return 'You must check your code using the MiraAgent.python_repl tool before submitting code. Please ensure you have all function and class information necessary and then use the MiraAgent.python_repl tool.'

    
    #no_repl version
    @tool()
    async def submit_code(self, code: str, agent: AgentRef, loop: LoopControllerRef) -> None:
        """
        Use this when you are ready to submit your code to the user.
        
        
        Ensure to handle any required dependencies, and provide a well-documented and efficient solution. Feel free to create helper functions or classes if needed.
        
        Please generate the code as if you were programming inside a Jupyter Notebook and the code is to be executed inside a cell.
        You MUST wrap the code with a line containing three backticks before and after the generated code like the code below but replace the 'triple_backticks':
        ```
        import mira
        ```

        No additional text is needed in the response, just the code block with the triple backticks.
        

        Args:
            code (str): python code block to be submitted to the user inside triple backticks.
        """
        loop.set_state(loop.STOP_SUCCESS)
        preamble, code, coda = re.split("```\w*", code)
        result = json.dumps(
            {
                "action": "code_cell",
                "language": "python3",
                "content": code.strip(),
            }
        )
        #check if successful then reset check code...
        return result

