import json
import logging
import re
from typing import Optional

import pandas

from archytas.react import Undefined
from archytas.tool_utils import AgentRef, LoopControllerRef, is_tool, tool, toolset

from beaker_kernel.lib.agent import BaseAgent
from beaker_kernel.lib.context import BaseContext

logger = logging.getLogger(__name__)


@toolset()
class BioToolset:
    """Toolset for Bio context"""

    def __init__(self):
        with open('context.json', 'r') as f:
            self.context_conf = json.load(f)

    @tool(autosummarize=True)
    async def generate_code(self, code_request: str, agent: AgentRef, loop: LoopControllerRef) -> None:
        """
        Use this if you are asked to generate code.

        You should ALWAYS think about what you need to do and search for functions that can help you.
        
        You should ALWAYS look at the docstrings for the functions in the code you write to determine how to use them.

        If any functions require additional arguments, please ask the user to provide these and do not guess at their values.

        Args:
            code_request (str): A fully grammatically correct description of what the code should do.
        """
        prompt = f"""
    You are tasked with writing Python code for various scientific tasks. You have some special libraries at your disposal, {self.context_conf.get('library_names')}, but can use other libraries if need be.

    You should ALWAYS try to use functions from one of the libraries {self.context_conf.get('library_names')} if you are able to find one or more functions from them that seem relevant to the task at hand.

    Please generate Python code to satisfy the user's request below.

        Request:
        ```
        {code_request}
        ```
    
    After you select a function or functions to use, you MUST look up the function docstring. This teaches you what arguments to use in the code.

    Read the function docstrings to learn how to use them. (Use <function>.__doc__ to read the docstring).

    Ensure to handle any required dependencies, and provide a well-documented and efficient solution. Feel free to create helper functions or classes if needed.

    Please generate the code as if you were programming inside a Jupyter Notebook and the code is to be executed inside a cell.
    You MUST wrap the code with a line containing three backticks (```) before and after the generated code.
    No addtional text is needed in the response, just the code block."""

        llm_response = await agent.query(prompt)
        loop.set_state(loop.STOP_SUCCESS)
        preamble, code, coda = re.split("```\w*", llm_response)
        result = json.dumps(
            {
                "action": "code_cell",
                "language": "python3",
                "content": code.strip(),
            }
        )
        return result

    generate_code.__doc__

    # @tool(autosummarize=True)
    # async def get_available_functions(self, package_name: str, agent: AgentRef) -> None:
    #     """
    #     You should ALWAYS try to run this on specific submodules, not entire libraries. For example, instead of running this on `Bio` you should
    #     run this function on `Bio.NaiveBayes`. In fact, there should almost always be a `.` in the `package_name` argument.
        
    #     This function should be used to discover the available functions in the target library or module and get an object containing their docstrings so you can figure out how to use them.

    #     This function will return an object and store it into self.__functions. The object will be a dictionary with the following structure:
    #     {
    #        function_name: <function docstring>,
    #        ...
    #     }

    #     Read the docstrings to learn how to use the functions and which arguments they take.

    #     Args:
    #         package_name (str): this is the name of the package to get information about. For example "Bio.NaiveBayes"
    #     """
    #     functions = {}
    #     code = agent.context.get_code("info", {"package_name": package_name})
    #     info_response = await agent.context.beaker_kernel.evaluate(
    #         code,
    #         parent_header={},
    #     )
    #     with open('/tmp/info.json', 'r') as f:
    #         info = json.loads(f.read())        
    #     for var_name, info in info.items():
    #         if var_name in functions:
    #             functions[var_name] = info
    #         else:
    #             functions[var_name] = info

    #     self.__functions = functions

    #     return functions

    # get_available_functions.__doc__


    @tool(autosummarize=True)
    async def search_functions(self, query: str, agent: AgentRef) -> None:
        """
        This function should be used to search for available functions that are available and relevant to the task described in the `query`.

        The query should be simple and specific and not overly verbose in order to yield the most relevant results.

        This function will return a search result object of the form:

        ```
        {'function_name': {
                        'description': 'description of the function here',
                        'docstring': 'the docstring of the function here'
                        },
        ...
        }
        ```

        You should then read the docstrings to learn how to use the functions and which arguments they take.

        Args:
            query (str): this is the query that describes the task against which you wish to find matching functions. This should be simple and specific."
        """
        code = agent.context.get_code("query_functions", {"query": query})
        function_results = await agent.context.beaker_kernel.evaluate(
            code,
            parent_header={},
        )
        return function_results


class BioAgent(BaseAgent):
    """
    You are assisting us in performing important scientific tasks.

    If you don't have the details necessary, you should use the ask_user tool to ask the user for them.
    """

    def __init__(self, context: BaseContext = None, tools: list = None, **kwargs):
        tools = [BioToolset]
        super().__init__(context, tools, **kwargs)
