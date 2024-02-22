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
        self.few_shot_examples=''
        self.code_blocks=[] #{'code':str,'execution_status':not_executed,executed_successfully,'execution_order':int,'output':output from running code block most recent time.}
        self.code_block_print='\n\n'.join([f'Code Block[{i}]: {self.code_blocks[i]["code"]}\nExecution Status:{self.code_blocks[i]["execution_status"]}\nExecution Order:{self.code_blocks[i]["execution_order"]}\nCode Block Output or Error:{self.code_blocks[i]["output"]}' for i in range(len(self.code_blocks))])
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

        variables=jupyter_context['user_vars']
        imported_modules=jupyter_context['imported_modules']
        return variables,imported_modules
    
    async def post_execute(self, message):
        self.variables,self.imported_modules=await self.get_jupyter_context()
        self.agent.debug(event_type="update_code_env",content={
                    "variables": self.variables,
                })
        self.agent.debug(event_type="code",content={
                    "imported_modules": self.imported_modules,
                })
    
    async def auto_context(self):
        from .procedures.python3.dynamic_example_selector import query_examples 
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
    
{self.few_shot_examples}
"""
        few_shot_logic_examples="""Here is an example of how to perform the workflow.
        User: 
        """
        
        intro_manual=f"""You are an exceptionally intelligent coding assistant that consistently delivers accurate and reliable responses to user instructions.
You should ALWAYS think about which functions and classes from mira you are going to use before you write code. Try to use mira as much as possible.
mira is a framework for representing systems using ontology-grounded meta-model templates, and generating various model implementations and exchange formats from these templates. 
It also implements algorithms for assembling and querying domain knowledge graphs in support of modeling.
You MUST lookup the function signature and docstring before using a function from mira. You can do so in the following ways: 
If the functions you want to use are in the context below, no need to look them up again.
Otherwise, either lookup the available functions from MiraToolset.get_available_functions, 
search for relevant functions and classes using MiraToolset.search_functions_classes 
or if you know the particular functions and classes you want to get more information on, use MiraToolset.get_functions_and_classes_docstring

Before you submit the code you have written to the user, you should use your MiraAgent.python_repl tool to make sure that the generated code is correct.
If any functions that you want to use in your code require additional arguments, please ask the user to provide these and do not guess at their values.
Once you have checked your code and ensure it is correct using your MiraAgent.python_repl tool, use the MiraAgent.submit_code tool to submit the code to the user's code environment. 

Below is some information on the submodules in mira:

mira.dkg - This module contains code for the construction of domain knowledge graphs.
mira.modeling - This module contains code for modeling. The top level contains the Model class, together with the Variable, Transition, and ModelParameter classes, used to represent a Model.
mira.metamodel - This module contains information on code related to meta models.
mira.sources - This module contains code to access models from different sources like json, url, etc..
mira.terarium_client - This module contains code which allows access to the terarium client. A web application for modeling. This module is not to be used.
mira.examples - This module contains examples of how to assemble and modify models in MIRA.

Additionally here are some similar examples of similar user requests and your previous successful code generations in the format [[Request,Code]].
If the request from the user is similar enough to one of these examples, use it to help write code to answer the user's request.
    
{self.few_shot_examples}
        """
        intro_manual2=f"""You are an exceptionally intelligent coding assistant that consistently delivers accurate and reliable responses to user instructions.
You should ALWAYS think about which functions and classes from mira you are going to use before you write code. Try to use mira as much as possible.
mira is a framework for representing systems using ontology-grounded meta-model templates, and generating various model implementations and exchange formats from these templates. 
It also implements algorithms for assembling and querying domain knowledge graphs in support of modeling.
You MUST lookup the function signature and docstring before using a function from mira. You can do so in the following ways: 
If the functions you want to use are in the context below, no need to look them up again.
Otherwise, first use the MiraToolset.search_functions_classes  to search for relevant functions and classes.
If that does not provide enough information, lookup the available functions for related modules using MiraToolset.get_available_functions, 
or if you know the particular functions and classes you want to get more information on, use MiraToolset.get_functions_and_classes_docstring

Before you submit the code you have written to the user, you should use your MiraAgent.python_repl tool to make sure that the generated code is correct.
If any functions that you want to use in your code require additional arguments, please ask the user to provide these and do not guess at their values.
Once you have checked your code and ensure it is correct using your MiraAgent.python_repl tool, use the MiraAgent.submit_code tool to submit the code to the user's code environment. 

Below is some information on the submodules in mira:

mira.dkg - This module contains code for the construction of domain knowledge graphs.
mira.modeling - This module contains code for modeling. The top level contains the Model class, together with the Variable, Transition, and ModelParameter classes, used to represent a Model.
mira.metamodel - This module contains information on code related to meta models.
mira.sources - This module contains code to access models from different sources like json, url, etc..
mira.terarium_client - This module contains code which allows access to the terarium client. A web application for modeling. This module is not to be used.
mira.examples - This module contains examples of how to assemble and modify models in MIRA.

Additionally here are some similar examples of similar user requests and your previous successful code generations in the format [[Request,Code]].
If the request from the user is similar enough to one of these examples, use it to help write code to answer the user's request.
    
{self.few_shot_examples}
        """
        intro_manual3=f"""You are an exceptionally intelligent coding assistant that consistently delivers accurate and reliable responses to user instructions.
mira is a framework for representing systems using ontology-grounded meta-model templates, and generating various model implementations and exchange formats from these templates. 
It also implements algorithms for assembling and querying domain knowledge graphs in support of modeling.

You should ALWAYS think about which functions and classes from mira you are going to use before you write code. Try to use mira as much as possible.
You can do so in the following ways: 
If the functions you want to use are in the context below, no need to look them up again.
Otherwise, first try to use the MiraToolset.search_functions_classes to search for relevant functions and classes.
If that does not provide enough information, lookup the available functions for related modules using MiraToolset.get_available_functions.

You MUST lookup the source code for each of the functions that you intend to use using the MiraToolset.get_functions_and_classes_source_code before using a function from mira.

Before you submit the code you have written to the user, you MUST use your MiraAgent.python_repl tool to make sure that the generated code is correct.
If any functions that you want to use in your code require additional arguments, please ask the user to provide these and do not guess at their values.
Once you have checked your code and ensure it is correct using your MiraAgent.python_repl tool, use the MiraAgent.submit_code tool to submit the code to the user's code environment. 

Below is some information on the submodules in mira:

mira.dkg - This module contains code for the construction of domain knowledge graphs.
mira.modeling - This module contains code for modeling. The top level contains the Model class, together with the Variable, Transition, and ModelParameter classes, used to represent a Model.
mira.metamodel - This module contains information on code related to meta models.
mira.sources - This module contains code to access models from different sources like json, url, etc..
mira.terarium_client - This module contains code which allows access to the terarium client. A web application for modeling. This module is not to be used.
mira.examples - This module contains examples of how to assemble and modify models in MIRA.

Additionally here are some similar examples of similar user requests and your previous successful code generations in the format [[Request,Code]].
If the request from the user is similar enough to one of these examples, use it to help write code to answer the user's request.
    
{self.few_shot_examples}
        """
        intro_manual3_no_few=f"""You are an exceptionally intelligent coding assistant that consistently delivers accurate and reliable responses to user instructions.
mira is a framework for representing systems using ontology-grounded meta-model templates, and generating various model implementations and exchange formats from these templates. 
It also implements algorithms for assembling and querying domain knowledge graphs in support of modeling.

You should ALWAYS think about which functions and classes from mira you are going to use before you write code. Try to use mira as much as possible.
You can do so in the following ways: 
If the functions you want to use are in the context below, no need to look them up again.
Otherwise, first try to use the MiraToolset.search_functions_classes to search for relevant functions and classes.
If that does not provide enough information, lookup the available functions for related modules using MiraToolset.get_available_functions.

You MUST lookup the information for each of the functions that you intend to use using the MiraToolset.get_functions_and_classes_docstring before using a function from mira.
If there are  mira specific input objects/classes be sure to look them up as well before using them as inputs.

Before you submit the code you have written to the user, you MUST use your MiraAgent.python_repl tool to make sure that the generated code is correct.
If any functions that you want to use in your code require additional arguments, please ask the user to provide these and do not guess at their values.
Once you have checked your code and ensure it is correct using your MiraAgent.python_repl tool, use the MiraAgent.submit_code tool to submit the code to the user's code environment. 

Below is some information on the submodules in mira:

mira.dkg - This module contains code for the construction of domain knowledge graphs.
mira.modeling - This module contains code for modeling. The top level contains the Model class, together with the Variable, Transition, and ModelParameter classes, used to represent a Model.
mira.metamodel - This module contains information on code related to meta models.
mira.sources - This module contains code to access models from different sources like json, url, etc..
mira.terarium_client - This module contains code which allows access to the terarium client. A web application for modeling. This module is not to be used.
mira.examples - This module contains examples of how to assemble and modify models in MIRA.
        """
        
        intro_manual3_no_few_no_repl=f"""You are an exceptionally intelligent coding assistant that consistently delivers accurate and reliable responses to user instructions.
mira is a framework for representing systems using ontology-grounded meta-model templates, and generating various model implementations and exchange formats from these templates. 
It also implements algorithms for assembling and querying domain knowledge graphs in support of modeling.

You should ALWAYS think about which functions and classes from mira you are going to use before you write code. Try to use mira as much as possible.
You can do so in the following ways: 
If the functions you want to use are in the context below, no need to look them up again.
Otherwise, first try to use the MiraToolset.search_functions_classes to search for relevant functions and classes.
If that does not provide enough information, lookup the available functions for related modules using MiraToolset.get_available_functions.

You MUST lookup the source code for each of the functions that you intend to use using the MiraToolset.get_functions_and_classes_source_code before using a function from mira.
If there are  mira specific input objects/classes be sure to look them up as well before using them as inputs.

Below is some information on the submodules in mira:

mira.dkg - This module contains code for the construction of domain knowledge graphs.
mira.modeling - This module contains code for modeling. The top level contains the Model class, together with the Variable, Transition, and ModelParameter classes, used to represent a Model.
mira.metamodel - This module contains information on code related to meta models.
mira.sources - This module contains code to access models from different sources like json, url, etc..
mira.terarium_client - This module contains code which allows access to the terarium client. A web application for modeling. This module is not to be used.
mira.examples - This module contains examples of how to assemble and modify models in MIRA.
        """
        
        intro_manual3_no_few_no_repl_all_classes=f"""You are an exceptionally intelligent coding assistant that consistently delivers accurate and reliable responses to user instructions.
mira is a framework for representing systems using ontology-grounded meta-model templates, and generating various model implementations and exchange formats from these templates. 
It also implements algorithms for assembling and querying domain knowledge graphs in support of modeling.

You should ALWAYS try looking up the what the user is asking you to do or portions of what the user is asking you to do in the documentation to get a sense of how it can be done.
You should ALWAYS think about which functions and classes from mira you are going to use before you write code. Try to use mira as much as possible.
You can do so in the following ways: 
If the functions you want to use are in the context below, no need to look them up again.
Otherwise, first try to use the MiraToolset.search_functions_classes to search for relevant functions and classes.
If that does not provide enough information, lookup the available functions for related modules using MiraToolset.get_available_functions.
If there is a main class or function you are using, you can lookup all the information on it and all the objects and functions required to use it using MiraToolset.get_class_or_function_full_information.
Use this when you want to instantiate a complicated object.

You can lookup source code for individual functions or classes using the MiraToolset.get_functions_and_classes_source_code before using a function from mira.

Below is some information on the submodules in mira:

mira.dkg - This module contains code for the construction of domain knowledge graphs.
mira.modeling - This module contains code for modeling. The top level contains the Model class, together with the Variable, Transition, and ModelParameter classes, used to represent a Model.
mira.metamodel - This module contains information on code related to meta models.
mira.sources - This module contains code to access models from different sources like json, url, etc..
mira.terarium_client - This module contains code which allows access to the terarium client. A web application for modeling. This module is not to be used.
mira.examples - This module contains examples of how to assemble and modify models in MIRA.
        """
        
        intro_manual3_few_no_repl_all_classes=f"""You are an exceptionally intelligent coding assistant that consistently delivers accurate and reliable responses to user instructions.
mira is a framework for representing systems using ontology-grounded meta-model templates, and generating various model implementations and exchange formats from these templates. 
It also implements algorithms for assembling and querying domain knowledge graphs in support of modeling.

You should ALWAYS try looking up the what the user is asking you to do or portions of what the user is asking you to do in the documentation to get a sense of how it can be done.
You should ALWAYS think about which functions and classes from mira you are going to use before you write code. Try to use mira as much as possible.
You can do so in the following ways: 
If the functions you want to use are in the context below, no need to look them up again.
Otherwise, first try to use the MiraToolset.search_functions_classes to search for relevant functions and classes.
If that does not provide enough information, lookup the available functions for related modules using MiraToolset.get_available_functions.
If there is a main class or function you are using, you can lookup all the information on it and all the objects and functions required to use it using MiraToolset.get_class_or_function_full_information.
Use this when you want to instantiate a complicated object.

You can lookup source code for individual functions or classes using the MiraToolset.get_functions_and_classes_source_code before using a function from mira.

Below is some information on the submodules in mira:

mira.dkg - This module contains code for the construction of domain knowledge graphs.
mira.modeling - This module contains code for modeling including visualization, ODE models, bilayer models, triples and amr representations like petrinets, regnets and stock and flow models. The top level contains the Model class,which together with the Variable, Transition, and ModelParameter classes, used to represent a Model.
mira.metamodel - This module contains information on code related to meta models.
mira.sources - This module contains code to access models from different sources like json, url, etc..
mira.terarium_client - This module contains code which allows access to the terarium client. A web application for modeling. This module is not to be used.
mira.examples - This module contains examples of how to assemble and modify models in MIRA.
        
Additionally here are some similar examples of similar user requests and your previous successful code generations in the format [[Request,Code]].
If the request from the user is similar enough to one of these examples, use it to help write code to answer the user's request.
    
{self.few_shot_examples}
"""

        '''If there is a main class or function you are using, you can lookup all the information on it and all the objects and functions required to use it using MiraToolset.get_class_or_function_full_information.
        Use this when you want to instantiate a complicated object.'''

        intro_manual3_few_repl_all_classes=f"""You are an exceptionally intelligent coding assistant that consistently delivers accurate and reliable responses to user instructions.
mira is a framework for representing systems using ontology-grounded meta-model templates, and generating various model implementations and exchange formats from these templates. 
It also implements algorithms for assembling and querying domain knowledge graphs in support of modeling.

You should ALWAYS try looking up the what the user is asking you to do or portions of what the user is asking you to do in the documentation to get a sense of how it can be done.
You should ALWAYS think about which functions and classes from mira you are going to use before you write code. Try to use mira as much as possible.
You can do so in the following ways: 
If the functions you want to use are in the context below, no need to look them up again.
Otherwise, first try to use the MiraToolset.get_available_functions to get the available functions in a related modules.
If that does not provide enough information, use the MiraToolset.search_functions_classes to search for relevant functions and classes.

You can lookup source code for individual functions or classes using the MiraToolset.get_functions_and_classes_source_code before using a function from mira.

Before you submit the code you have written to the user, you MUST use your MiraAgent.python_repl tool to make sure that the generated code is correct.
If any functions that you want to use in your code require additional arguments, please ask the user to provide these and do not guess at their values.
Once you have checked your code and ensure it is correct using your MiraAgent.python_repl tool, use the MiraAgent.submit_code tool to submit the code to the user's code environment. 

Below is some information on the submodules in mira:

mira.dkg - This module contains code for the construction of domain knowledge graphs.
mira.modeling - This module contains code for modeling including visualization, ODE models, bilayer models, triples and amr representations like petrinets, regnets and stock and flow models. The top level contains the Model class,which together with the Variable, Transition, and ModelParameter classes, used to represent a Model.
mira.metamodel - This module contains information on code related to meta models such as TemplateModels.
mira.sources - This module contains code to access models from different sources like json, url, etc..
mira.terarium_client - This module contains code which allows access to the terarium client. A web application for modeling. This module is not to be used.
mira.examples - This module contains examples of how to assemble and modify models in MIRA.
        
Additionally here are some similar examples of similar user requests and your previous successful code generations in the format [[Request,Code]].
If the request from the user is similar enough to one of these examples, use it to help write code to answer the user's request.
    
{self.few_shot_examples}
"""
        
        code_environment=f"""These are the variables in the user's current code environment with key value pairs:
{self.variables}

The user has also imported the following modules: {','.join(self.imported_modules)}. So you don't need to import them when generating code.
When writing code that edits the variables that the user has in their environment be sure to modify them in place. 
For example if we have a variable a=1, if we wanted to change a to 2, we you write a=2.
When the user asks you to perform an action, if they specifically mention a variable name, be sure to use that variable.
Additionally if the object they ask you to update is similar to an object in the code environment, be sure to use that variable. 

Here are the functions that you have looked up the docstrings of using the MiraToolset.get_functions_and_classes_docstring tool so far - 
{self.functions}
"""

        code_environment2=f"""These are the variables in the user's current code environment with key value pairs:
{self.variables}

The user has also imported the following modules: {','.join(self.imported_modules)}. So you don't need to import them when generating code.
When writing code that edits the variables that the user has in their environment be sure to modify them in place. 
For example if we have a variable a=1, if we wanted to change a to 2, we you write a=2.
When the user asks you to perform an action, if they specifically mention a variable name, be sure to use that variable.
Additionally if the object they ask you to update is similar to an object in the code environment, be sure to use that variable. 
"""

        code_environment_notebook_rep=f"""These are the variables in the user's current code environment with key value pairs:
{self.variables}

The user has also imported the following modules: {','.join(self.imported_modules)}. So you don't need to import them when generating code.
When writing code that edits the variables that the user has in their environment be sure to modify them in place. 
For example if we have a variable a=1, if we wanted to change a to 2, we you write a=2.

Here are the functions that you have looked up the docstrings of using the MiraToolset.get_functions_and_classes_docstring tool so far - 
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
            module = import_module(package)

            # Redirect the standard output to capture the help text
            with io.StringIO() as buf, contextlib.redirect_stdout(buf):
                help(module)
                # Store the help text in the dictionary
                documentation[package] = buf.getvalue()
        print(f"Fetched help for {documentation.keys()}")
        return documentation
    