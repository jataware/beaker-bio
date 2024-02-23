# -*- coding: utf-8 -*-
#DONE: test on more examples
#TODO: maybe just get whole chain or file of examples and append to the description to be sure??
#TODO: improve llm file filtering
#TODO: add compilation check?
#TODO: improve example extraction on chirho. 
#TODO: generate examples..
from src.beaker_bio_context.procedures.python3.embed_docs import *
from nbconvert import PythonExporter

def get_examples_from_code_doc_file(file_path,notebook=False,doc_file=False): #this may be a false dichotomy .. some docs have .ipynb in them..
    #TODO: change so that description is more similar to a user request..
    multiple_examples_in_examples_py_file_prompt='''The code below contains several examples of how to use the chirho library.
    Please break the code into different sections, each of which contains an example and give a short description of the example. 
    Give the start line and stop line of each example section, any imports or code from previous section which are required to make the example section compile properly 
    and short description of the example. Please format your answer in json format as follows: [{"start_line":int,"stop_line":int,"description":str,"required_code_additions":str}] with one dict per example. 
    Note that the required code additions will be placed at the top of the code block. Please ensure that all required code additions are complete (do not use statements like put in your code here...)
    Here is the code with the line number alongside each line:\n''' #to change dynamically on new context creation
    documentation_extract_examples_prompt='''There are some number of code examples in this documentation file. 
    Extract each code example and give a short description of the example. 
    Be sure to include all code from previous examples which is required to get the code example to compile (each code example should stand on its own) . 
    Please format in json format as follows: [{"code": str, "description":str}] with one dict per example. 
    If therer are no code examples in the documentation file then simply return an empty array in json format (ie [])

    Documentation - \n''' #TODO: add to prompt to allow for no code..
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

def does_this_file_contain_examples(code_file_contents):
    prompt="""Below is the content of a file from the chirho library. 
    Does this file contain examples of how to use the code or does it only contain source code with no examples? 
    Please format your answer in json format as follows: {{"answer":[Yes/No]}}
    {code_file_contents}""" #to change dynamically on new context creation
    res=ask_gpt(full_prompt,'gpt-4-0125-preview',response_format={"type": "json_object"})
    return res['answer']

def process_directory(directory):
    example_code_files,example_doc_files=filter_directory(directory)
    examples_json=[]
    if len(example_doc_files)>0:
        doc_files_results=process_files(example_doc_files,True)
        for key in doc_files_results:
            if type(doc_files_results[key])==dict:
                if 'code_examples' in doc_files_results[key].keys():
                    code_examples=doc_files_results[key]['code_examples']#TODO: do a better job of enforcing format to remove this..
                else:
                    code_examples=doc_files_results[key]
            else:
                code_examples=doc_files_results[key]
            if type(code_examples)==list:
                for item in code_examples:
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
    filter_prompt="""Below is the content and file path of a file from the chirho library. 
    Does this file contain examples of how to use the code or does it only contain source code with no examples? 
    Please format your answer in json format as follows: {{"answer":[Yes/No]}}
    File Path: {file_path}
    File Contents: {file_contents}""" #to change dynamically on new context creation
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
    
true_code_examples=[]  

true_doc_examples =["/media/hdd/Code/beaker-bio/src/beaker_bio_context/chiro/documentation/actual_causality.ipynb",
"/media/hdd/Code/beaker-bio/src/beaker_bio_context/chiro/documentation/backdoor.ipynb",
"/media/hdd/Code/beaker-bio/src/beaker_bio_context/chiro/documentation/cevae.ipynb",
"/media/hdd/Code/beaker-bio/src/beaker_bio_context/chiro/documentation/conf.py",
"/media/hdd/Code/beaker-bio/src/beaker_bio_context/chiro/documentation/contributing.rst",
"/media/hdd/Code/beaker-bio/src/beaker_bio_context/chiro/documentation/counterfactual.rst",
"/media/hdd/Code/beaker-bio/src/beaker_bio_context/chiro/documentation/deepscm.ipynb",
"/media/hdd/Code/beaker-bio/src/beaker_bio_context/chiro/documentation/dr_learner.ipynb",
"/media/hdd/Code/beaker-bio/src/beaker_bio_context/chiro/documentation/dynamical.rst",
"/media/hdd/Code/beaker-bio/src/beaker_bio_context/chiro/documentation/dynamical_intro.ipynb",
"/media/hdd/Code/beaker-bio/src/beaker_bio_context/chiro/documentation/dynamical_type_aliases.rst",
"/media/hdd/Code/beaker-bio/src/beaker_bio_context/chiro/documentation/explainable.rst",
"/media/hdd/Code/beaker-bio/src/beaker_bio_context/chiro/documentation/getting_started.rst",
"/media/hdd/Code/beaker-bio/src/beaker_bio_context/chiro/documentation/index.rst",
"/media/hdd/Code/beaker-bio/src/beaker_bio_context/chiro/documentation/indexed.rst",
"/media/hdd/Code/beaker-bio/src/beaker_bio_context/chiro/documentation/interventional.rst",
"/media/hdd/Code/beaker-bio/src/beaker_bio_context/chiro/documentation/mediation.ipynb",
"/media/hdd/Code/beaker-bio/src/beaker_bio_context/chiro/documentation/observational.rst",
"/media/hdd/Code/beaker-bio/src/beaker_bio_context/chiro/documentation/refs.bib",
"/media/hdd/Code/beaker-bio/src/beaker_bio_context/chiro/documentation/requirements.txt",
"/media/hdd/Code/beaker-bio/src/beaker_bio_context/chiro/documentation/robust.rst",
"/media/hdd/Code/beaker-bio/src/beaker_bio_context/chiro/documentation/sciplex.ipynb",
"/media/hdd/Code/beaker-bio/src/beaker_bio_context/chiro/documentation/sdid.ipynb",
"/media/hdd/Code/beaker-bio/src/beaker_bio_context/chiro/documentation/slc.ipynb",
"/media/hdd/Code/beaker-bio/src/beaker_bio_context/chiro/documentation/tutorial_i.ipynb"]

