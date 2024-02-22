# -*- coding: utf-8 -*-
#DONE: test on more examples
#TODO: maybe just get whole chain or file of examples and append to the description to be sure??
#TODO: improve llm file filtering
#TODO: add compilation check?
from src.beaker_bio_context.procedures.python3.embed_docs import *
from nbconvert import PythonExporter

def get_examples_from_code_doc_file(file_path,notebook=False,doc_file=False):
    #TODO: change so that description is more similar to a user request..
    multiple_examples_in_examples_py_file_prompt='''The code below contains several examples of how to use the mira library.
    Please break the code into different sections, each of which contains an example and give a short description of the example. 
    Give the start line and stop line of each example section, any imports or code from previous section which are required to make the example section compile properly 
    and short description of the example. Please format your answer in json format as follows: [{"start_line":int,"stop_line":int,"description":str,"required_code_additions":str}] with one dict per example. 
    Note that the required code additions will be placed at the top of the code block. Please ensure that all required code additions are complete (do not use statements like put in your code here...)
    Here is the code with the line number alongside each line:\n'''
    documentation_extract_examples_prompt='''There are some number of code examples in this documentation file. 
    Extract each code example and give a short description of the example. 
    Be sure to include all code from previous examples which is required to get the code example to compile (each code example should stand on its own) . 
    Please format in json format as follows: [{"code": str, "description":str}] with one dict per example. 

    Documentation - \n'''
    #TODO: improve this especially on documentation that has source files which include code blocks..
    #TODO: maybe try version with line numbers to force exact extraction..?
    if notebook: # Provide the path to your notebook file
        exporter = PythonExporter()
        python_code,_=exporter.from_filename(file_path)
        lines=python_code.split('\n')
    else:
        with open(file_path, 'r') as file:
            # Read all lines into a list
            lines = file.readlines()
    for i,line in enumerate(lines):
       lines[i]=line.strip()
    print_out=''
    for i,line in enumerate(lines):
        print_out+=f'Line {i}: {line}\n'
    if doc_file:
        full_prompt=documentation_extract_examples_prompt+print_out
        res=ask_gpt(full_prompt,'gpt-4-0125-preview',response_format={"type": "json_object"})
        return json.loads(res)
    else:
        full_prompt=multiple_examples_in_examples_py_file_prompt+print_out
        res=ask_gpt(full_prompt,'gpt-4-0125-preview',response_format={"type": "json_object"})
        code_examples=[]
        if type(json.loads(res))==list:
            examples=json.loads(res)
        else:
            examples=json.loads(res)['examples']
        for example in examples:
            code_examples.append({'code':example['required_code_additions']+'\n'+'\n'.join(lines[example['start_line']:example['stop_line']]),'description':example['description']})
         #TODO: add something to fix paths in code examples?   
        return code_examples

example_res='''Here is the breakdown of the code into different sections, each accompanied by its description, start and stop lines, and any required code from previous sections to compile properly:

```json
[
  {
    "start_line": 18,
    "stop_line": 33,
    "description": "Defines a basic SIR (Susceptible, Infected, Recovered) model using the mira library.",
    "required_code_additions": "from mira.metamodel import ControlledConversion, NaturalConversion, TemplateModel\nfrom .concepts import susceptible, infected, recovered"
  },
  {
    "start_line": 35,
    "stop_line": 63,
    "description": "Defines a parameterized SIR model adding parameters and initial values for populations, demonstrating a more detailed configuration.",
    "required_code_additions": "from copy import deepcopy as _d\nimport sympy\nfrom mira.metamodel import ControlledConversion, NaturalConversion, TemplateModel, Initial, Parameter, safe_parse_expr\nfrom .concepts import susceptible, infected, recovered"
  },
  {
    "start_line": 66,
    "stop_line": 95,
    "description": "Illustrates the creation of a two-city SIR model, where susceptible, infected, and recovered individuals can move between the cities.",
    "required_code_additions": "from mira.metamodel import ControlledConversion, NaturalConversion, TemplateModel\nfrom .concepts import susceptible, infected, recovered\ninfection = ControlledConversion(subject=susceptible, outcome=infected, controller=infected)\nrecovery = NaturalConversion(subject=infected, outcome=recovered)"
  },
  {
    "start_line": 97,
    "stop_line": 111,
    "description": "Shows a data structure configuration for a bilayer SIR model, highlighting how model data can be organized in a non-standard, custom format.",
    "required_code_additions": ""
  },
  {
    "start_line": 113,
    "stop_line": 132,
    "description": "Defines an SVIR (Susceptible, Verbally Infected, Infected, Recovered) model, distinguishing between symptomatic and asymptomatic infections.",
    "required_code_additions": "from mira.metamodel import GroupedControlledConversion, NaturalConversion, TemplateModel\nfrom .concepts import susceptible, infected_symptomatic, infected_asymptomatic, recovered"
  },
  {
    "start_line": 134,
    "stop_line": 149,
    "description": "Updates a previously defined parameterized SIR model with normalized initial values and unit specifications, suitable for documentation and testing purposes.",
    "required_code_additions": "from copy import deepcopy as _d\nimport sympy\nfrom mira.metamodel import TemplateModel, SympyExprStr, Unit\nfrom .concepts import susceptible, infected, recovered\nsir_parameterized = _d(your_previous_sir_parameterized_definition_here) # Ensure you replace 'your_previous_sir_parameterized_definition_here' with the actual variable or structure."
  }
]
```'''
#note this example must be run from mira.examples dir where it was extracted from..
example_1='\n'.join(lines[18:35])
example_1='from mira.metamodel import ControlledConversion, NaturalConversion, TemplateModel\nfrom .concepts import susceptible, infected, recovered'

mira_examples=["/media/hdd/Code/beaker-bio/src/beaker_bio_context/examples/metamodel_intro.ipynb",
"/media/hdd/Code/beaker-bio/src/beaker_bio_context/examples/model_api.ipynb",
"/media/hdd/Code/beaker-bio/src/beaker_bio_context/examples/regnets.ipynb",
"/media/hdd/Code/beaker-bio/src/beaker_bio_context/examples/simulation.ipynb"]
mira_code_examples=[]
for example in mira_examples:
    mira_code_examples.append(get_examples_from_code_doc_file(example,notebook=True))


def does_this_file_contain_examples(code_file_contents):
    prompt="""Below is the content of a file from the mira library. 
    Does this file contain examples of how to use the code or does it only contain source code with no examples? 
    Please format your answer in json format as follows: {{"answer":[Yes/No]}}
    {code_file_contents}"""
    res=ask_gpt(full_prompt,'gpt-4-0125-preview',response_format={"type": "json_object"})
    return res['answer']

def process_directory(directory):
    example_code_files,example_doc_files=filter_directory(directory)
    examples_json=[]
    if len(example_doc_files)>0:
        doc_files_results=process_files(example_doc_files,True)
        for key in doc_files_results:
            if type(doc_files_results[key])==list:
                for item in doc_files_results[key]:
                    code = item['code']
                    if not code.startswith('```') :code='```'+code
                    if not code.endswith('```'):code=code+'```' #add ``` to enforce json format of code agent via examples.
                    examples_json.append({'origination_source_type':'doc_file',
                                          'origination_source':key,
                                          'origination_method':'extract_from_library_automatic',
                                          'code':item['code'],
                                          'description':item['description']})
    if len(example_code_files)>0:
        code_files_results=process_files(example_code_files,False)
        for key in code_files_results:
            if type(code_files_results[key])==list:
                for item in code_files_results[key]:
                    code = item['code']
                    if not code.startswith('```') :code='```'+code
                    if not code.endswith('```'):code=code+'```' #add ``` to enforce json format of code agent via examples.
                    examples_json.append({'origination_source_type':'code_file',
                                          'origination_source':key,
                                          'origination_method':'extract_from_library_automatic',
                                          'code':code, 
                                          'description':item['description']})
                    #TODO: add compilation check, maybe later??
    json.dump(examples_json,open(f'{directory.replace("/","_")}_extracted_code_examples.json','w')) 
    return  examples_json     
        
    
    
    
    
def filter_directory(directory):
    filter_prompt="""Below is the content and file path of a file from the mira library. 
    Does this file contain examples of how to use the code or does it only contain source code with no examples? 
    Please format your answer in json format as follows: {{"answer":[Yes/No]}}
    File Path: {file_path}
    File Contents: {file_contents}"""
    files=glob.glob(directory+'/**',recursive=True) 
    documentation_files=[file for file in files if file.endswith('.rst') or file.endswith('.md')]
    code_files=[file for file in files if file.endswith('.py') or file.endswith('.ipynb')]
    #TODO: add some manual filtering, size of contents, __init__.py??
    #check code files to see if they contain examples - 
    code_lines=[]
    for code_file in code_files:
        if code_file.endswith('.ipynb'):
            exporter = PythonExporter()
            python_code,_=exporter.from_filename(file_path)
            code_lines.append(python_code)
        else:
            code_lines.append('\n'.join(open(code_file).readlines()))
    
    prompts={code: filter_prompt.format(file_contents=code_lines[i],file_path=code)
             for i,code in enumerate(code_files)}
    
    #TODO: add kill requests if most requests are done and it is hanging to parallel call in embed_docs..
    responses=process_ask_gpt_in_parallel(prompts.values(), prompts.keys(), model='gpt-4-0125-preview',max_workers=8,response_format={"type": "json_object"})
    example_code_files=[]
    for key in responses:
        try:
            if json.loads(responses[key])['answer']=='Yes':
                example_code_files.append(key)
        except:
            print(f'{key} was not filtered properly')
    
    #check doc files to see if they contain examples - 
    prompts={doc: filter_prompt.format(file_contents='\n'.join(open(doc).readlines()),file_path=doc)
             for doc in documentation_files}
    
    #TODO: add kill requests if most requests are done and it is hanging to parallel call in embed_docs..
    responses=process_ask_gpt_in_parallel(prompts.values(), prompts.keys(), model='gpt-4-0125-preview',max_workers=8,response_format={"type": "json_object"})
    example_doc_files=[]
    for key in responses:
        try:
            if json.loads(responses[key])['answer']=='Yes':
                example_doc_files.append(key)
        except:
            print(f'{key} was not filtered properly')
    
    return example_code_files,example_doc_files

def process_files(example_files,doc_files=False):
    #pass in a list of either code files or doc file path strings
    results = {}
    with ThreadPoolExecutor() as executor:
        futures = {executor.submit(get_examples_from_code_doc_file, file,file.endswith('.ipynb'),doc_files): file for file in example_files}
        for future in as_completed(futures):
            file = futures[future]
            try:
                result = future.result()
                results[file] = result
            except Exception as e:
                print(f"Error processing file '{file}': {e}")    
    return results
    
true_code_examples=['/media/hdd/Code/beaker-bio/src/beaker_bio_context/code/examples/decapodes/decapodes_examples.py',
                    '/media/hdd/Code/beaker-bio/src/beaker_bio_context/code/examples/chime.py',
                    "/media/hdd/Code/beaker-bio/src/beaker_bio_context/code/examples/concepts.py",
                    "/media/hdd/Code/beaker-bio/src/beaker_bio_context/code/examples/jin2022.py",
                    "/media/hdd/Code/beaker-bio/src/beaker_bio_context/code/examples/mech_bayes.py",
                    "/media/hdd/Code/beaker-bio/src/beaker_bio_context/code/examples/nabi2021.py",
                    "/media/hdd/Code/beaker-bio/src/beaker_bio_context/code/examples/sir.py",
                    "/media/hdd/Code/beaker-bio/src/beaker_bio_context/examples/ASKEM MIRA demo.ipynb",
"/media/hdd/Code/beaker-bio/src/beaker_bio_context/examples/biomodels.ipynb",
"/media/hdd/Code/beaker-bio/src/beaker_bio_context/examples/DKG RDF Demo.ipynb",
"/media/hdd/Code/beaker-bio/src/beaker_bio_context/examples/dkg_api.ipynb",
"/media/hdd/Code/beaker-bio/src/beaker_bio_context/examples/Entity Similarity Demo.ipynb",
"/media/hdd/Code/beaker-bio/src/beaker_bio_context/examples/Hackathon Scenario 1.ipynb",
"/media/hdd/Code/beaker-bio/src/beaker_bio_context/examples/Hackathon Scenario 2 - Find Models with Hospitalizations.ipynb",
"/media/hdd/Code/beaker-bio/src/beaker_bio_context/examples/Hackathon Scenario 3.ipynb",
"/media/hdd/Code/beaker-bio/src/beaker_bio_context/examples/Hackathon Scenario 4.ipynb",
"/media/hdd/Code/beaker-bio/src/beaker_bio_context/examples/metamodel_intro.ipynb",
"/media/hdd/Code/beaker-bio/src/beaker_bio_context/examples/model_api.ipynb",
"/media/hdd/Code/beaker-bio/src/beaker_bio_context/examples/Rapid construction of new DKGs.ipynb",
"/media/hdd/Code/beaker-bio/src/beaker_bio_context/examples/regnets.ipynb",
"/media/hdd/Code/beaker-bio/src/beaker_bio_context/examples/simulation.ipynb",
"/media/hdd/Code/beaker-bio/src/beaker_bio_context/examples/System Dynamics Ingestion.ipynb",
"/media/hdd/Code/beaker-bio/src/beaker_bio_context/examples/TA1 Extraction Evaluation.ipynb",
"/media/hdd/Code/beaker-bio/src/beaker_bio_context/examples/viz_strat_petri.ipynb",
"/media/hdd/Code/beaker-bio/src/beaker_bio_context/examples/web_client.ipynb",
"/media/hdd/Code/beaker-bio/src/beaker_bio_context/examples/applications/Bevacizumab_pharmacokinetics.ipynb",
"/media/hdd/Code/beaker-bio/src/beaker_bio_context/examples/applications/Enzyme_substrate_kinetics.ipynb",
"/media/hdd/Code/beaker-bio/src/beaker_bio_context/examples/ensemble/ensemble.ipynb",
"/media/hdd/Code/beaker-bio/src/beaker_bio_context/examples/evaluation_2023.01/Scenario1.ipynb",
"/media/hdd/Code/beaker-bio/src/beaker_bio_context/examples/evaluation_2023.01/Scenario2.ipynb",
"/media/hdd/Code/beaker-bio/src/beaker_bio_context/examples/evaluation_2023.01/Scenario3.ipynb",
"/media/hdd/Code/beaker-bio/src/beaker_bio_context/examples/evaluation_2023.07/Ensemble Evaluation Model 1.ipynb",
"/media/hdd/Code/beaker-bio/src/beaker_bio_context/examples/evaluation_2023.07/scenario1.ipynb",
"/media/hdd/Code/beaker-bio/src/beaker_bio_context/examples/evaluation_2023.07/scenario2.ipynb",
"/media/hdd/Code/beaker-bio/src/beaker_bio_context/examples/evaluation_2023.07/scenario3.ipynb",
"/media/hdd/Code/beaker-bio/src/beaker_bio_context/examples/hackathon_2023.07/scenario1-2-wastewater.ipynb",
"/media/hdd/Code/beaker-bio/src/beaker_bio_context/examples/hackathon_2023.07/scenario1.ipynb",
"/media/hdd/Code/beaker-bio/src/beaker_bio_context/examples/hackathon_2023.07/scenario2.ipynb",
"/media/hdd/Code/beaker-bio/src/beaker_bio_context/examples/hackathon_2023.10/climate_grounding.ipynb",
"/media/hdd/Code/beaker-bio/src/beaker_bio_context/examples/hackathon_2023.10/dkg_grounding_model_comparison.ipynb",
"/media/hdd/Code/beaker-bio/src/beaker_bio_context/examples/hackathon_2023.10/Ingesting Decapode Compute Graph Demo.ipynb",
"/media/hdd/Code/beaker-bio/src/beaker_bio_context/examples/hackathon_2023.10/stratification_autoname.ipynb"]  

true_doc_examples =[]            
#TODO: do mira in parallel.. #detect file type by extension (.rst,.md,.py,.ipynb)

