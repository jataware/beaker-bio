import logging
import contextlib
from importlib import import_module
import io
import json
from typing import TYPE_CHECKING, Any, Dict
import pandas as pd
import os

from beaker_kernel.lib.context import BaseContext
from .agent import Agent

if TYPE_CHECKING:
    from beaker_kernel.kernel import LLMKernel
    from .new_base_agent import NewBaseAgent
    from beaker_kernel.lib.subkernels.base import BaseSubkernel

logger = logging.getLogger(__name__)

class Context(BaseContext):
    slug = "bio"
    agent_cls: "NewBaseAgent" = Agent

    def __init__(
        self,
        beaker_kernel: "LLMKernel",
        subkernel: "BaseSubkernel",
        config: Dict[str, Any],
    ) -> None:
        with open('context.json','r') as f:
            self.context_conf = json.loads(f.read())
        self.library_name="Mimi.jl"
        self.sub_module_description=[]#self.context_conf.get('library_submodule_descriptions', '')
        self.functions = {}
        self.config = config
        self.variables={}
        self.imported_modules={}
        self.available_modules={}
        self.few_shot_examples=''
        self.code_blocks=[] #{'code':str,'execution_status':not_executed,executed_successfully,'execution_order':int,'output':output from running code block most recent time.}
        self.code_block_print='\n\n'.join([f'Code Block[{i}]: {self.code_blocks[i]["code"]}\nExecution Status:{self.code_blocks[i]["execution_status"]}\nExecution Order:{self.code_blocks[i]["execution_order"]}\nCode Block Output or Error:{self.code_blocks[i]["output"]}' for i in range(len(self.code_blocks))])
        super().__init__(beaker_kernel, subkernel, self.agent_cls, config)
        
    async def get_jupyter_context(self):
        imported_modules=[]
        variables={}
        code = self.agent.context.get_code("get_jupyter_variables")
        response = await self.agent.context.beaker_kernel.evaluate(
            code,
            parent_header={},
        )
        jupyter_context=response["return"]
        logger.error(jupyter_context)

        variables=jupyter_context['user_vars']
        imported_modules=jupyter_context['imported_modules']
        available_modules=jupyter_context['available_modules']

        return variables, imported_modules, available_modules
    
    async def post_execute(self, message):
        self.variables,self.imported_modules, self.available_modules=await self.get_jupyter_context()
        self.agent.debug(event_type="update_code_env",content={
                    "variables": self.variables,
                })
        self.agent.debug(event_type="code",content={
                    "imported_modules": self.imported_modules,
                })
        self.agent.debug(event_type="code",content={
                    "available_modules": self.available_modules,
                })
    
    async def auto_context(self):
        from .lib.dynamic_example_selector import query_examples
        await self.get_jupyter_context()
        most_recent_user_query=''
        for message in self.agent.messages:
            if message['role']=='user':
                most_recent_user_query=message['content']
        if most_recent_user_query!=self.agent.most_recent_user_query:
            self.few_shot_examples=query_examples(most_recent_user_query)
            self.agent.debug(event_type="few_shot_examples",content={
                        "few_shot_examples": self.few_shot_examples,
                        "user_query":most_recent_user_query
                    })
        
        intro = f"""
You are {self.subkernel.KERNEL_NAME} software engineer whose goal is to help with {self.context_conf.get('task_description', 'doing things')} in {self.library_name}.
You should ALWAYS think about which functions and classes from {self.library_name} you are going to use before you write code.
You MUST have the function signature and docstring handy before using a function. 
If the functions you want to use are in the context below, no need to look them up again.
Otherwise, either lookup the available functions from Toolset.get_available_functions, 
search for relevant functions and classes using Toolset.skill_search 
or if you know the particular functions and classes you want to get more information on, use Toolset.get_functions_and_classes_docstring

Below is a dictionary of library help information where the library name is the key
and the help documentation the value:

{await self.retrieve_documentation()}

Additionally here are some similar examples of similar user requests and your previous successful code generations:
    
{self.few_shot_examples}
"""
        few_shot_logic_examples="""Here is an example of how to perform the workflow.
        User: 
        """
        
        intro_manual=f"""You are an exceptionally intelligent coding assistant that consistently delivers accurate and reliable responses to user instructions.
You should ALWAYS think about which functions and classes from {self.library_name} you are going to use before you write code. Try to use {self.library_name} as much as possible.
{self.library_name} is a framework for representing systems using ontology-grounded meta-model templates, and generating various model implementations and exchange formats from these templates. 
It also implements algorithms for assembling and querying domain knowledge graphs in support of modeling.
You MUST lookup the function signature and docstring before using a function from {self.library_name}. You can do so in the following ways: 
If the functions you want to use are in the context below, no need to look them up again.
Otherwise, either lookup the available functions from Toolset.get_available_functions, 
search for relevant functions and classes using Toolset.search_functions_classes 
or if you know the particular functions and classes you want to get more information on, use Toolset.get_functions_and_classes_docstring

Below is some information on the submodules in {self.library_name}:

{self.sub_module_description}

Additionally here are some similar examples of similar user requests and your previous successful code generations in the format [[Request,Code]].
If the request from the user is similar enough to one of these examples, use it to help write code to answer the user's request.
    
{self.few_shot_examples}
        """
        intro_manual2=f"""You are an exceptionally intelligent coding assistant that consistently delivers accurate and reliable responses to user instructions.
You should ALWAYS think about which functions and classes from {self.library_name} you are going to use before you write code. Try to use {self.library_name} as much as possible.
{self.library_name} is a framework for representing systems using ontology-grounded meta-model templates, and generating various model implementations and exchange formats from these templates. 
It also implements algorithms for assembling and querying domain knowledge graphs in support of modeling.
You MUST lookup the function signature and docstring before using a function from {self.library_name}. You can do so in the following ways: 
If the functions you want to use are in the context below, no need to look them up again.
Otherwise, first use the Toolset.search_functions_classes  to search for relevant functions and classes.
If that does not provide enough information, lookup the available functions for related modules using Toolset.get_available_functions, 
or if you know the particular functions and classes you want to get more information on, use Toolset.get_functions_and_classes_docstring

Below is some information on the submodules in {self.library_name}:

{self.sub_module_description}

Additionally here are some similar examples of similar user requests and your previous successful code generations in the format [[Request,Code]].
If the request from the user is similar enough to one of these examples, use it to help write code to answer the user's request.
    
{self.few_shot_examples}
        """
        intro_manual3=f"""You are an exceptionally intelligent coding assistant that consistently delivers accurate and reliable responses to user instructions.
{self.library_name} is a framework for representing systems using ontology-grounded meta-model templates, and generating various model implementations and exchange formats from these templates. 
It also implements algorithms for assembling and querying domain knowledge graphs in support of modeling.

You should ALWAYS think about which functions and classes from {self.library_name} you are going to use before you write code. Try to use {self.library_name} as much as possible.
You can do so in the following ways: 
If the functions you want to use are in the context below, no need to look them up again.
Otherwise, first try to use the Toolset.search_functions_classes to search for relevant functions and classes.
If that does not provide enough information, lookup the available functions for related modules using Toolset.get_available_functions.

You MUST lookup the source code for each of the functions that you intend to use using the Toolset.get_functions_and_classes_source_code before using a function from {self.library_name}.

Below is some information on the submodules in {self.library_name}:

{self.sub_module_description}

Additionally here are some similar examples of similar user requests and your previous successful code generations in the format [[Request,Code]].
If the request from the user is similar enough to one of these examples, use it to help write code to answer the user's request.
    
{self.few_shot_examples}
        """
        intro_manual3_no_few=f"""You are an exceptionally intelligent coding assistant that consistently delivers accurate and reliable responses to user instructions.
{self.library_name} is a framework for representing systems using ontology-grounded meta-model templates, and generating various model implementations and exchange formats from these templates. 
It also implements algorithms for assembling and querying domain knowledge graphs in support of modeling.

You should ALWAYS think about which functions and classes from {self.library_name} you are going to use before you write code. Try to use {self.library_name} as much as possible.
You can do so in the following ways: 
If the functions you want to use are in the context below, no need to look them up again.
Otherwise, first try to use the Toolset.search_functions_classes to search for relevant functions and classes.
If that does not provide enough information, lookup the available functions for related modules using Toolset.get_available_functions.

You MUST lookup the information for each of the functions that you intend to use using the Toolset.get_functions_and_classes_docstring before using a function from {self.library_name}.
If there are  {self.library_name} specific input objects/classes be sure to look them up as well before using them as inputs.

Below is some information on the submodules in {self.library_name}:

{self.sub_module_description}
        """
        
        intro_manual3_no_few_no_repl=f"""You are an exceptionally intelligent coding assistant that consistently delivers accurate and reliable responses to user instructions.
{self.library_name} is a framework for representing systems using ontology-grounded meta-model templates, and generating various model implementations and exchange formats from these templates. 
It also implements algorithms for assembling and querying domain knowledge graphs in support of modeling.

You should ALWAYS think about which functions and classes from {self.library_name} you are going to use before you write code. Try to use {self.library_name} as much as possible.
You can do so in the following ways: 
If the functions you want to use are in the context below, no need to look them up again.
Otherwise, first try to use the Toolset.search_functions_classes to search for relevant functions and classes.
If that does not provide enough information, lookup the available functions for related modules using Toolset.get_available_functions.

You MUST lookup the source code for each of the functions that you intend to use using the Toolset.get_functions_and_classes_source_code before using a function from {self.library_name}.
If there are  {self.library_name} specific input objects/classes be sure to look them up as well before using them as inputs.

Below is some information on the submodules in {self.library_name}:

{self.sub_module_description}
        """
        
        intro_manual3_no_few_no_repl_all_classes=f"""You are an exceptionally intelligent coding assistant that consistently delivers accurate and reliable responses to user instructions.
{self.library_name} is a framework for representing systems using ontology-grounded meta-model templates, and generating various model implementations and exchange formats from these templates. 
It also implements algorithms for assembling and querying domain knowledge graphs in support of modeling.

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
        """
        
        intro_manual3_few_no_repl_all_classes=f"""You are an exceptionally intelligent coding assistant that consistently delivers accurate and reliable responses to user instructions.
{self.library_name} is a framework for representing systems using ontology-grounded meta-model templates, and generating various model implementations and exchange formats from these templates. 
It also implements algorithms for assembling and querying domain knowledge graphs in support of modeling.

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
"""

        '''If there is a main class or function you are using, you can lookup all the information on it and all the objects and functions required to use it using Toolset.get_class_or_function_full_information.
        Use this when you want to instantiate a complicated object.'''

        intro_manual3_few_repl_all_classes=f"""You are an exceptionally intelligent coding assistant that consistently delivers accurate and reliable responses to user instructions.
{self.library_name} is a framework for representing systems using ontology-grounded meta-model templates, and generating various model implementations and exchange formats from these templates. 
It also implements algorithms for assembling and querying domain knowledge graphs in support of modeling.

You should ALWAYS try looking up the what the user is asking you to do or portions of what the user is asking you to do in the documentation to get a sense of how it can be done.
You should ALWAYS think about which functions and classes from {self.library_name} you are going to use before you write code. Try to use {self.library_name} as much as possible.
You can do so in the following ways: 
If the functions you want to use are in the context below, no need to look them up again.
Otherwise, first try to use the Toolset.get_available_functions to get the available functions in a related modules.
If that does not provide enough information, use the Toolset.search_functions_classes to search for relevant functions and classes.

You can lookup source code for individual functions or classes using the Toolset.get_functions_and_classes_source_code before using a function from {self.library_name}.

Below is some information on the submodules in {self.library_name}:

{self.sub_module_description}
        
Additionally here are some similar examples of similar user requests and your previous successful code generations in the format [[Request,Code]].
If the request from the user is similar enough to one of these examples, use it to help write code to answer the user's request.
    
{self.few_shot_examples}
"""
        
        code_environment=f"""These are the variables in the user's current code environment with key value pairs:
{self.variables}

The user has also imported the following modules: {','.join(self.imported_modules)}.
The following models have NOT been imported but are available: {','.join(self.imported_modules)}.
So you don't need to import them when generating code.
When writing code that edits the variables that the user has in their environment be sure to modify them in place. 
For example if we have a variable a=1, if we wanted to change a to 2, we you write a=2.
When the user asks you to perform an action, if they specifically mention a variable name, be sure to use that variable.
Additionally if the object they ask you to update is similar to an object in the code environment, be sure to use that variable. 

Here are the functions that you have looked up the docstrings of using the Toolset.get_functions_and_classes_docstring tool so far - 
{self.functions}
"""

        code_environment2=f"""These are the variables in the user's current code environment with key value pairs:
{self.variables}

The user has also imported the following modules: {','.join(self.imported_modules)}.
The following models have NOT been imported but are available: {','.join(self.imported_modules)}.
So you don't need to import them when generating code.
When writing code that edits the variables that the user has in their environment be sure to modify them in place. 
For example if we have a variable a=1, if we wanted to change a to 2, we you write a=2.
When the user asks you to perform an action, if they specifically mention a variable name, be sure to use that variable.
Additionally if the object they ask you to update is similar to an object in the code environment, be sure to use that variable. 
"""

        code_environment_notebook_rep=f"""These are the variables in the user's current code environment with key value pairs:
{self.variables}

The user has also imported the following modules: {','.join(self.imported_modules)}.
The following models have NOT been imported but are available: {','.join(self.imported_modules)}.
So you don't need to import them when generating code.
When writing code that edits the variables that the user has in their environment be sure to modify them in place. 
For example if we have a variable a=1, if we wanted to change a to 2, we you write a=2.

Here are the functions that you have looked up the docstrings of using the Toolset.get_functions_and_classes_docstring tool so far - 
{self.functions}

Here are the code blocks in the user's notebook along with their execution status and order and the outputs of each code block if it has been run:
{self.code_block_print}
"""
        outro = f"""
Please answer any user queries or perform user instructions to the best of your ability, but do not guess if you are not sure of an answer.
"""

        result = "\n".join([intro_manual3_few_no_repl_all_classes,code_environment2,outro])
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

            code = self.agent.context.get_code("get_module_docs", {"module": package})
            response = await self.agent.context.beaker_kernel.evaluate(
                code,
                parent_header={},
            )
            docs = response["return"]
            documentation[package] = docs
        print(f"Fetched help for {documentation.keys()}")
        return documentation