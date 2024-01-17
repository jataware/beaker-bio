import logging
import contextlib
from importlib import import_module
import io
import json
from typing import TYPE_CHECKING, Any, Dict

from beaker_kernel.lib.context import BaseContext
from beaker_kernel.lib.subkernels.python import PythonSubkernel

from .agent import BioAgent

if TYPE_CHECKING:
    from beaker_kernel.kernel import LLMKernel
    from beaker_kernel.lib.agent import BaseAgent
    from beaker_kernel.lib.subkernels.base import BaseSubkernel

logger = logging.getLogger(__name__)

class BioContext(BaseContext):
    slug = "bio"
    agent_cls: "BaseAgent" = BioAgent

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
        with open('context.json','r') as f:
            self.context_conf = json.loads(f.read())        
        super().__init__(beaker_kernel, subkernel, self.agent_cls, config)

    async def auto_context(self):
        intro = f"""
You are python software engineer whose goal is to help with {self.context_conf.get('task_description'), 'doing things'} in {self.metadata.get("name", "a Jupyter notebook")}.

You have access to the following library information which you should use to discover what is available within a package and determine the proper syntax and functionality on how to use the code.
Querying against the module or package should list all avialable submodules and functions that exist, so you can use this to discover available
functions and the query the function to get usage information. Below is a dictionary of library help information where the library name is the key
and the help documentation the value:

{await self.retrieve_documentation()}
"""
        outro = f"""
Please answer any user queries to the best of your ability, but do not guess if you are not sure of an answer.
"""

        result = "\n".join([intro, outro])
        return result

    async def retrieve_documentation(self):
        """
        Get's the specified libraries help documentation and stores it into a dictionary:
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