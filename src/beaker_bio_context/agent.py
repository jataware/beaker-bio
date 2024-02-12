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
#DONE: get rid of dang argument checker in archytas and then clone that repo.. copy, pip install -e . - worked around it

#DONE: add syncing with the jupyter notebook or otherwise keeping a similar environment to the notebook without final code running in the notebook.

#DONE: change the repl to not have persistent state but rather to mirror jupyter state. Agent needs to write all code 
#DONE: give agent variables in autoconfig that tell it about the variables in the jupyter env.. or maybe here is the code that has already been run and the variables created..
#TODO: add descriptions to code env objects being passed around in a generic way..
#TODO: try using gpt 3.5..
#TODO: replace skill search with basic code file parsing (from my codegen agent), call it code search..
#TODO: rewrite files in easyTool format using gpt-3.5..
#TODO: add few shot examples of actual flow (ie conversations)
#DONE: tell it to modify variables in place..
#TODO: try examples from darpa-askem beaker mira examples..
#TODO: add list of state variables that were instantiated to few shot example search?
#TODO: add custom within react loop summarization.. save to variable then put in autocontext?
#TODO: should I just reset between sumbit code calls?
#TODO: add function sigs to info return
#TODO: add knowledge of state of notebook to context keys - _ih, _oh (in and out full lists)
#TODO: hybrid or keyword search??
@tool()
def python_repl(code: str, agent: AgentRef) -> str:
        """
        Tool which can be used to run python code. Use this to check correctness of your code before you submit it to the user.
        Runs python code in a python environment.
        
        The initial setup of the environment will be a copy of the user's environment, including instantiated variables and imported modules.
        The environment is not persistent between runs, so any variables created will not be available in subsequent runs.
        The only visible effects of this tool are from output to stdout/stderr. If you want to view a result, you MUST print it.
        Remember, if you are confused in any way about how to use a library, make sure to call `help(module_name)` to learn as much as you can.
        
        Args:
            code (str): The code to run
        
        Returns:
            str: The stdout output and standard error of the code
        """
        repl_locals=agent.context.variables
        repl_modules=agent.context.imported_modules
        captured_stdout = io.StringIO()
        captured_stderr = io.StringIO()
        sys.stdout = captured_stdout
        sys.stderr = captured_stderr
        code='\n'.join([f'import {module}' for module in repl_modules])+'\n'+code
        try:
            exec(code, repl_locals)
        except Exception as e:
            sys.stderr.write(str(e))
            
        # restore stdout/stderr
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
        
        return captured_stdout.getvalue(), captured_stderr.getvalue()
    
# class MiraPythonTool(PythonTool):
#     """
#     Tool which can be used to run python code. Use this to check correctness of your code before you submit it to the user.
#     """
#     @tool()
#     def run(self, code: str) -> str:
#         """
#         Runs python code in a python environment.
        
#         The initial setup of the environment will be a copy of the user's environment, including instantiated variables and imported modules.
#         The environment is not persistent between runs, so any variables created will not be available in subsequent runs.
#         The only visible effects of this tool are from output to stdout/stderr. If you want to view a result, you MUST print it.
#         Remember, if you are confused in any way about how to use a library, make sure to call `help(module_name)` to learn as much as you can.
        
#         Args:
#             code (str): The code to run
        
#         Returns:
#             str: The stdout output of the code
#         """
#         out, err = self.env.run_script(code)
#         if err:
#             raise Exception(err)
        
#         return out


@toolset()
class MiraToolset:
    """Toolset for Mira context"""
#    @tool(autosummarize=True)
#    async def generate_code_using_lats(self, query: str, agent: AgentRef) -> None:
#        use_lats(query,model='gpt-3.5-turbo-1106',tree_depth=2)#'gpt-4-1106-preview''gpt-4-1106-preview'

    #generate_code.__doc__

    @tool(autosummarize=True)
    async def get_available_functions(self, package_name: str, agent: AgentRef) -> None:
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
    
    @tool(autosummarize=True)
    async def get_functions_and_classes_docstring(self, list_of_function_or_class_names: list, agent: AgentRef) -> None:
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

    get_available_functions.__doc__

    #TODO: not really working for ODEs.. not sure it works well in general...
    #TODO: change to multiple queries?
    @tool(autosummarize=True)
    async def skill_search(self, query: str, agent: AgentRef) -> None:
        """
        This function should be used to search for available classes, functions and methods that are available and relevant to the task described in the `query`.

        The query should be simple and specific and not overly verbose in order to yield the most relevant results.

        This function will return a search result object of the form:

        ```
        {'function_or_class_name': {
                        'description': 'description of the function here',
                        'docstring': 'the docstring of the function here',
                        'source_code': 'the source code of the function here',
                        },
        ...
        }
        ```

        You should then read the docstrings and the source code to learn how to use the functions/classes/etc and which arguments they take and methods they have.

        Args:
            query (str): this is the query that describes the task against which you wish to find matching functions. This should be simple and specific."
        """
        from .procedures.python3.query_functions import query_functions
        return query_functions(query)


class MiraAgent(NewBaseAgent):
    """
    You are assisting us in performing important scientific tasks.

    If you don't have the details necessary, you should use the ask_user tool to ask the user for them.
    """

    def __init__(self, context: BaseContext = None, tools: list = None, **kwargs):
        tools = [MiraToolset,python_repl]
        super().__init__(context, tools, **kwargs)
        with open('context.json', 'r') as f:
            self.context_conf = json.load(f)
            
# Here is an example of a code block to be submitted - 
# ```
# from mira.sources.biomodels import get_template_model
# template_model = get_template_model('BIOMD0000000956')
# ```  

  
    @tool()
    async def submit_code(self, code: str, agent: AgentRef, loop: LoopControllerRef) -> None:
        """
        Use this after you have checked your code using the python_repl tool and are ready to submit your code to the user.
        
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
        return result
