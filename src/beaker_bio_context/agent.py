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

@toolset()
class Toolset:
    """Toolset for our context"""

    @tool(autosummarize=True)
    async def get_available_functions(self, package_name: str, agent: AgentRef):
        """
        Querying against the module or package should list all available submodules and functions that exist, so you can use this to discover available
        functions and the query the function to get usage information.
        You should ALWAYS try to run this on specific submodules, not entire libraries.
        
        This function should be used to discover the available functions in the target library or module and get an object containing their docstrings so you can figure out how to use them.

        This function will return an object and store it into self.__functions. The object will be a dictionary with the following structure:
        {
            function_name: <function docstring>,
            ...
        }

        Read the docstrings to learn how to use the functions and which arguments they take.

        Args:
            package_name (str): this is the name of the package to get information about.
        """
        functions = {}

        
        documentation = {}

        code = self.agent.context.get_code("info", {"module": package_name})
        response = await self.agent.context.beaker_kernel.evaluate(
            code,
            parent_header={},
        )
        functions = response["return"]
        print(f"Fetched func info")
        agent.context.functions.update(functions)
        return functions            
    
    
    @tool(autosummarize=True)
    async def get_functions_docstring(self, list_of_function_names: list, agent: AgentRef):
        """
        Use this tool to additional information on individual function such as their inputs, outputs and description (and generally anything else that would be in a docstring)
        You should ALWAYS use this tool before writing or checking code to check the function signatures of the functions you are about to use.
        
        Read the information returned to learn how to use the function and which arguments they take.
        
        The function names used in the input to this tool should include the entire module hierarchy
        
        Args:
            list_of_function_names (list): this is a list of the the names of the functions and/or classes to get information about. 
        """
        #TODO: figure out cause of this and remove ugly filter
        if type(list_of_function_names)==dict:
            list_of_function_names=list_of_function_names['list_of_function_names']

        code = self.agent.context.get_code("info", {"from_module": "false", "function_names": ",".join(list_of_function_names)})
        response = await self.agent.context.beaker_kernel.evaluate(
            code,
            parent_header={},
        )
        functions = response["return"]
        help_string=''
        for name, help_text in functions.items():
            help_string+=f'{name}: {help_text}'
            agent.context.functions[name]=help_text
        return help_string
    
    # @tool(autosummarize=True)
    # async def get_functions_source_code(self, list_of_function_names: list, agent: AgentRef):
    #     """
    #     Use this tool to additional information on individual function or class such as their inputs, outputs and description (and generally anything else that would be in a docstring)
    #     You should ALWAYS use this tool before writing or checking code to check the function signatures of the functions or classes you are about to use.
        
    #     Read the information returned to learn how to use the function or class and which arguments they take.
        
    #     The function and class names used in the input to this tool should include the entire module hierarchy
        
    #     Args:
    #         list_of_function_names (list): this is a list of the the names of the functions and/or classes to get information about.
    #     """
    #     #TODO: figure out cause of this and remove ugly filter
    #     if type(list_of_function_names)==dict:
    #         list_of_function_names=list_of_function_names['list_of_function_names']

    #     code = self.agent.context.get_code("info", {"from_module": "false", "return_source": "true", "function_names": ",".join(list_of_function_names)})
    #     response = await self.agent.context.beaker_kernel.evaluate(
    #         code,
    #         parent_header={},
    #     )
    #     functions = response["return"]
    #     help_string=''
    #     for name, help_text in functions.items():
    #         help_string+=f'{name}: {help_text}'
    #     return help_string
    
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
        Use this tool to search the code in the Mimi repo for function and classes relevant to your query.
        Input should be a natural language query meant to find information in the documentation as if you were searching on a search bar.
        Response will be a string with the top few results, each result will have the function or class doc string and the source code (which includes the function signature)
        
        Args:
            query (str): Natural language query. Some Examples - "ode model", "sir model", "using dkg package"
        """
        from .procedures.python3.embed_functions_classes_2 import query_functions_classes
        return query_functions_classes(query)



class Agent(NewBaseAgent):
    """
    You are assisting us in performing important scientific tasks.

    If you don't have the details necessary, you should use the ask_user tool to ask the user for them.
    """

    def __init__(self, context: BaseContext = None, tools: list = None, **kwargs):
        tools = [Toolset]
        super().__init__(context, tools, **kwargs)
        with open('context.json', 'r') as f:
            self.context_conf = json.load(f)
        self.most_recent_user_query=''
        self.checked_code=False
        self.code_attempts=0
    
    #no_repl version
    @tool()
    async def submit_code(self, code: str, agent: AgentRef, loop: LoopControllerRef) -> None:
        """
        Use this when you are ready to submit your code to the user.
        
        
        Ensure to handle any required dependencies, and provide a well-documented and efficient solution. Feel free to create helper functions or classes if needed.
        
        Please generate the code as if you were programming inside a Jupyter Notebook and the code is to be executed inside a cell.
        You MUST wrap the code with a line containing three backticks before and after the generated code like the code below but replace the "triple_backticks":
        ```
        import DataFrames
        ```

        No additional text is needed in the response, just the code block with the triple backticks.

        Args:
            code (str): code block to be submitted to the user inside triple backticks.
        """        
        loop.set_state(loop.STOP_SUCCESS)
        preamble, code, coda = re.split("```\w*", code)
        result = json.dumps(
            {
                "action": "code_cell",
                "language": self.context.subkernel.KERNEL_NAME,
                "content": code.strip(),
            }
        )
        #check if successful then reset check code...
        return result

