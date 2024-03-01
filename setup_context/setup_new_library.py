# -*- coding: utf-8 -*-
import json
context=json.load(open('context.json','r'))
library_name=context["library_names"][0]
#Now we need to encode the information from your code and documentation.
#First, to setup the documentation - 
from src.beaker_bio_context.procedures.python3.embed_documents import embed_documents
embed_documents(f'src/beaker_bio_context/{library_name}/documentation')

#Now we will extract functions and classes from the code - 
from src.beaker_bio_context.procedures.python3.embed_functions_classes_2 import embed_functions_and_classes
embed_functions_and_classes(f'src/beaker_bio_context/{library_name}/code',library_name=library_name)


#Now extract examples and encode them -
from extract_examples import process_doc_files,process_code_files
docs_json=process_doc_files(context['doc_files'])
code_json=process_code_files(context['code_files'])
examples_json=docs_json+code_json           
json.dump(examples_json,open(f'{library_name}_extracted_code_examples.json','w'))
from src.beaker_bio_context.procedures.python3.dynamic_example_selector import add_examples
add_examples(f'{library_name}_extracted_code_examples.json')

#Finally we need to update the doc strings of our agent file - 
from set_names import update_agent_doc_strings
update_agent_doc_strings(context['library_names'][0],
context['submodule_examples'][0],
context['class_examples'][0],
context['class_method_example'][0],
context['function_examples'][0],
context['documentation_query_examples'][0]
)