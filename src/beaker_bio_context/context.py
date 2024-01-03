from typing import TYPE_CHECKING, Any, Dict

from beaker_kernel.lib.context import BaseContext
from beaker_kernel.lib.subkernels.python import PythonSubkernel

from .agent import BioAgent

if TYPE_CHECKING:
    from beaker_kernel.kernel import LLMKernel
    from beaker_kernel.lib.agent import BaseAgent
    from beaker_kernel.lib.subkernels.base import BaseSubkernel


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
        super().__init__(beaker_kernel, subkernel, self.agent_cls, config)

    async def auto_context(self):
        intro = f"""
You are python software engineer whose goal is to help with dataset manipulation in {self.metadata.get("name", "a Jupyter notebook")}.

You have access to the python library called Bio. The Bio library is part of the BioPython Project is an international association of developers of freely available Python tools for computational molecular biology. 

It has access to the following functions:
{await self.get_available_functions()}
"""
        outro = f"""
Please answer any user queries to the best of your ability, but do not guess if you are not sure of an answer.
"""

        result = "\n".join([intro, outro])
        return result

    async def get_available_functions(self, parent_header={}):
        """
        This function should be used to discover the available functions in the Bio library and get an object containing their docstrings so you can figure out how to use them.

        This function will return an object and store it into self.bio_functions. The object will be a dictionary with the following structure:
        {
           function_name: <function docstring>,
           ...
        }

        Args:
            parent_header (dict, optional): Not used currently. Defaults to {}.
        """
        code = self.get_code("info")
        info_response = await self.beaker_kernel.evaluate(
            code,
            parent_header=parent_header,
        )
        info = info_response.get("return")
        for var_name, info in info.items():
            if var_name in self.functions:
                self.functions[var_name] = info
            else:
                self.functions[var_name] = info