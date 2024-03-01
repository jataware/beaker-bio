# -*- coding: utf-8 -*-

#given a description of the repository ask questions on how to use that repo..
############################ SIMPLE ########################################
'''
This workflow will work better to improve and test code repo performance when we already have decent baseline performance or some examples.
'''
###########GET EXAMPLES ################
make_examples_base_queries="""
What are some queries that a user could ask or request they could make to learn more about or use the mira library. Give me 10 examples
""" 
#do this with the beaker agent or maybe with some subset of tools??
make_examples_base_instructions="""
What are some instructions that a user could give that you could fulfill using the mira library. Give me 10 examples
"""
#then add code writing portion to the request..
code_writing_portion_queries="{request}\nPlease provide a code example that includes of the code necessary to setup the objects required by the example."

code_writing_portion_instructions="Please write code that can be compiled and contains all necessary objects. {request}"

#TODO: maybe try all 10 of these or at least the valid ones and see the success rate..
#TODO: make this programatic
#TODO: try with gpt3.5?
example_requests_1=["How can I create a domain knowledge graph using mira?",
"What is the process for defining a new concept in mira's meta-model?",
"Can you show me how to convert a meta-model into a Petri net using mira?",
"How do I serialize a model to JSON format in mira?",
"What are the steps to visualize a model using mira's graphical visualization tools?",
"How can I integrate mira with other Python libraries for model analysis?",
"Can you explain how to use mira to simulate an epidemiological model?",
"What functions are available in mira for querying and manipulating knowledge graphs?",
"How do I use mira to generate exchange formats from meta-model templates?",
"Can you provide an example of using mira to assemble a model from various data sources?"]

example_requests_2=["Create a simple SIR epidemiological model using mira."
"Generate a JSON file from a model template using mira.",
"Visualize the structure of a domain knowledge graph.",
"Assemble a model with SEIRD compartments and parameters.",
"Convert a model into a Petri net representation.",
"Query a metaregistry to find identifiers for biological concepts.",
"Create a model that includes vaccination strategies and their impact on disease spread.",
"Simulate the dynamics of an epidemiological model over time.",
"Integrate domain knowledge from multiple sources into a coherent model.",
"Use the terarium client to interact with a remote modeling service."]

################ COMPILING AND DEBUGGIN ##############
debug_response="""It looks like there was an error with the code you submitted, can you fix it? Here is the traceback -{traceback}""" #do this like x3-x5 or maybe this a good time for LATS.. maybe add some reflection to this prompt
debug_response="""It looks like there was an error with the code you submitted, can you fix it? Please reflect on the reason for the error as well as additional information on functions, classes or otherwise that you might need. Then use your tools to get that information. Here is the traceback -{traceback}""" #do this like x3-x5 or maybe this a good time for LATS.. maybe add some reflection to this prompt
debug_response_examples=""" There was an error in the code you generated, can you fix it? Here are some examples of using {function_with_error} : {examples}. \n Here is the traceback - {traceback}"""

answer_llm_query="""You have submitted a request to the mira agent, whose purpose is to help you use the {library_name} library. {library_description}. Your request was : {request}. 
In order to complete your request, the agent has a question. Please answer the question in json format similar to the following: {{"answer":your_answer}}
"""
#TODO: extract examples splitting is creating some issues..
ask_for_code="""Please generate code to do so.""" #if there was no code generated, check by looking at agent tools..
import io
import sys
import traceback

def check_python_code(code:str,repl_locals={},repl_modules={}):
    """
    
    Args:
        code (str): The code to run
        
    
    """
    captured_stdout = io.StringIO()
    captured_stderr = io.StringIO()
    sys.stdout = captured_stdout
    sys.stderr = captured_stderr
    code = '\n'.join([f'import {module}' for module in repl_modules]) +'\n' + code

    traceback_str=''
    print_out='\n'
    try:
        exec(code, repl_locals)
        return True,'Success!'
    except Exception as e:
        traceback_str = traceback.format_exc()
        return False, traceback_str

res,txt=check_python_code('import os',{},{}) #TODO: finish test
#check for compile
#get local vars and imports..

################## DETERMINE SUCCESS #######################
#make judgement on response y/n
make_judgement="""You have submitted a request to the mira agent, whose purpose is to help you use the {library_name} library. 
{library_description}
Your request was : {request}
The agent's response was : 
{agent_response}

Does the agent's response properly fulfill your request? Please format your response in the following json format - {{"reasoning":why you gave the answer you gave,"answer":[Yes/No]}}
"""


#maybe give source code related to the error objects..
make_judgement_example={'library_name':'mira',
                        'library_description':'''Mira is a framework for representing systems using ontology-grounded meta-model templates, and generating various model implementations and exchange formats from these templates. 
                        It also implements algorithms for assembling and querying domain knowledge graphs in support of modeling.''',
                        'request':'Can you show me how to define a meta-model template in mira?',
                        'agent_response':'''from mira.metamodel.templates import Template, ControlledConversion, NaturalConversion, Concept

# Define concepts
subject = Concept(name='subject')
controller = Concept(name='controller')
outcome = Concept(name='outcome')

# Define a controlled conversion process
controlled_conversion = ControlledConversion(
    controller=controller,
    subject=subject,
    outcome=outcome
)

# Define a natural conversion process
natural_conversion = NaturalConversion(
    subject=subject,
    outcome=outcome
)

# Create a meta-model template
meta_model_template = Template(
    name='Example Meta-Model Template',
    display_name='Example Meta-Model',
    controlled_conversions=[controlled_conversion],
    natural_conversions=[natural_conversion]
)'''}


#or prompts evolution alla that instruct paper..
#or adversarial prompt..
#or conversation


########### VOYAGER STYLE --- building up skills (examples..) like version ###########
#TODO: make this programatic
#TODO: try with gpt3.5?
#TODO: try this on another class programatically without using few shot examples..
#TODO: maybe break this into several calls that can be done in parallel instead of one conversation if possible (no performance degradation..)
#TODO: try without tool use?
'''
This workflow will hopefully help build examples and allow use of higher level classes and functions without examples. Could be combined with simple pipeline after..
'''
#get all the examples you can from extracted examples for use in this then..

#start from the module then get the most important classes (from examples or random code). Trace required objects all the back to the most basic objects then work your way up..
#maybe build ast diagram??
#Maybe start from top and on failures work your way down?

#/home/ryan/Downloads/get_mira_examples_TemplateModel.ipynb contains this journey, I skipped the SpecifiedTemplate part though..
#example top->down
# metamodel.io.model_to_json_file(model: TemplateModel, fname): -> TemplateModel
# metamodel.template_model.TemplateModel -> Initial, Observable, Annotations, Time, SpecifiedTemplate, SympyExprStr, Parameter
# metamodel.template_model.Initial -> Concept
# metamodel.templates.Concept
level_0_code_gen_prompt2="""Can you write several different examples of how to instantiate a {class_or_function_name} from {code_location}? Please make sure that your examples can be compiled and run. Please make sure that all necessary module are imported. Here is the related source code :{source_code}""" #change to use instead of instantiate for function.. Then also maybe instantiate and use for classes?
level_0_code_gen_prompt="""Can you write an example of how to instantiate a {class_or_function_name}? Here is the related source code : {source_code}""" #to improve, request more examples.. 
#grab any other classes instantiated and create examples from them..
level_0_additional_examples_prompt="""Can you instantiate {class_or_function_name} in any other ways? Please provide examples if so."""
