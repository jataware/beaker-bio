import logging
import contextlib
from importlib import import_module
import io
import json
from typing import TYPE_CHECKING, Any, Dict
import pickle
import os

from beaker_kernel.lib.context import BaseContext
from beaker_kernel.lib.subkernels.python import PythonSubkernel
import pkgutil
from .agent import MiraAgent

if TYPE_CHECKING:
    from beaker_kernel.kernel import LLMKernel
    from .new_base_agent import NewBaseAgent
    from beaker_kernel.lib.subkernels.base import BaseSubkernel

logger = logging.getLogger(__name__)

class MiraContext(BaseContext):
    slug = "bio"
    agent_cls: "NewBaseAgent" = MiraAgent

    def __init__(
        self,
        beaker_kernel: "LLMKernel",
        subkernel: "BaseSubkernel",
        config: Dict[str, Any],
    ) -> None:
        if not isinstance(subkernel, PythonSubkernel):
            raise ValueError("This context is only valid for Python.")
        self.functions = {}
        self.config = config
        self.variables={}
        self.imported_modules={}
        with open('context.json','r') as f:
            self.context_conf = json.loads(f.read())        
        super().__init__(beaker_kernel, subkernel, self.agent_cls, config)
        
    async def get_jupyter_context(self):
        imported_modules=[]
        variables={}
        code = self.agent.context.get_code("get_jupyter_variables")
        await self.agent.context.beaker_kernel.evaluate(
            code,
            parent_header={},
        )
        jupyter_context={'user_vars':{},'imported_modules':[]}
        try:
            jupyter_context=pickle.load(open('/tmp/jupyter_state.pkl', 'rb'))
        except:
            logger.error('failed to load jupyter_state.pkl')
            logger.error(os.path.exists('/tmp/jupyter_state.pkl'))
        # jupyter_context = jupyter_context.get('return')
        # logger.error(jupyter_context)
        variables=jupyter_context['user_vars']
        imported_modules=jupyter_context['imported_modules']
        self.agent.debug('Variables:')
        self.agent.debug(variables)
        self.agent.debug('imported_modules:')
        self.agent.debug(imported_modules)
        return variables,imported_modules
    async def auto_context(self):
        variables,imported_modules=await self.get_jupyter_context()
        
        from .procedures.python3.dynamic_example_selector import query_examples 
        most_recent_user_query=''
        for message in self.agent.messages:
            if message['role']=='user':
                most_recent_user_query=message['content']
        few_shot_examples=query_examples(most_recent_user_query)
        
        
        intro = f"""
You are python software engineer whose goal is to help with {self.context_conf.get('task_description', 'doing things')} in {self.metadata.get("name", "a Jupyter notebook")}.
You should ALWAYS think about which functions and classes from mira you are going to use before you write code.
You MUST have the function signature and docstring handy before using a function. 
If the functions you want to use are in the context below, no need to look them up again.
Otherwise, either lookup the available functions from MiraToolset.get_available_functions, 
search for relevant functions and classes using MiraToolset.skill_search 
or if you know the particular functions and classes you want to get more information on, use MiraToolset.get_functions_and_classes_docstring

Before you submit the code you have written to the user, you should use your python_repl tool to make sure that the generated code is correct.
If any functions that you want to use in your code require additional arguments, please ask the user to provide these and do not guess at their values.
Once you have checked your code and ensure it is correct using your python_repl tool, use the submit_code tool to submit the code to the user's code environment. 

Below is a dictionary of library help information where the library name is the key
and the help documentation the value:

{await self.retrieve_documentation()}

Additionally here are some similar examples of similar user requests and your previous successful code generations:
    
{few_shot_examples}
"""

        code_environment=f"""These are the variables in the user's current code environment with key value pairs:
            {variables}

The user has also imported the following modules: {','.join(imported_modules)}. So you don't need to import them when generating code.
When writing code that edits the variables that the user has in their environment be sure to modify them in place. 
For example if we have a variable a=1, if we wanted to change a to 2, we you write a=2.

Here are the functions that you have looked up the docstrings of using the MiraToolset.get_functions_and_classes_docstring tool so far - 
{self.functions}
"""
        outro = f"""
Please answer any user queries or perform user instructions to the best of your ability, but do not guess if you are not sure of an answer.
"""

        result = "\n".join([intro,code_environment,outro])
        return result
    
    async def retrieve_documentation(self):
        """
        Gets the specified libraries help documentation and stores it into a dictionary:
        {   
            "package_name": "help documentation",
            ....
        }
        """
        documentation = {}
        for package in self.context_conf.get('library_names', []):
            module = import_module(package)

            # Redirect the standard output to capture the help text
            with io.StringIO() as buf, contextlib.redirect_stdout(buf):
                help(module)
                # Store the help text in the dictionary
                documentation[package] = buf.getvalue()
        print(f"Fetched help for {documentation.keys()}")
        return documentation
    