# -*- coding: utf-8 -*-
import os
import chromadb
import openai
import json
def start_chromadb(docker=False,collection_name="chirho_examples",path="/bio_context/chromabd_functions"): #to change dynamically on new context creation

    if docker:
        #Initialize ChromaDB client and create a collection
        client = chromadb.HttpClient(host='localhost', port=8000)
    else:
        chroma_client = chromadb.PersistentClient(path=path)
    
    collection = chroma_client.get_or_create_collection(name=collection_name)
    
    openai.api_key = os.environ['OPENAI_API_KEY']
    return collection
#TODO: change example format to the same as what the agent will see?
#TODO: change examples to conversations?
#TODO: change search to look for code similar to the code in the current notebook? (requires openai embeddings..)
def add_examples(json_files:list=['_media_hdd_Code_beaker-bio_src_beaker_bio_context_chiro_code_extracted_code_examples2.json']): #to change dynamically on new context creation
    user_queries_or_descriptions=[]
    code_strings=[]
    metadatas=[]
    for file in json_files:
        examples=json.load(open(file,'r'))
        for example in examples:
            user_queries_or_descriptions.append(example['description'])
            code_strings.append(example['code'])
            metadatas.append({'origination_method':example['origination_method'],
                              'origination_source':example['origination_source'],
                              'origination_source_type':example['origination_source_type']})
    #TODO: add check for existing docs..
    u_query_collection=start_chromadb(collection_name="chirho_user_queries_dev6",path="./chromabd_functions") #to change dynamically on new context creation
    u_query_collection.add(
        documents=['Request: ' + query for query in user_queries_or_descriptions],
        metadatas=metadatas, #TODO: maybe add functions or classes in the code examples for easier lookup?
        ids=[str(i) for i in range(len(user_queries_or_descriptions))] #TODO: make more descriptive?
    )
    #separate index for user queries then just use sim search on query?
    examples_collection=start_chromadb(collection_name="chirho_examples_dev6",path="./chromabd_functions") #to change dynamically on new context creation
    examples_collection.add(
        documents=code_strings, #add back Code: ?
        metadatas=metadatas, #TODO: maybe add functions or classes in the code examples for easier lookup?
        ids=[str(i) for i in range(len(code_strings))] #make more descriptive?
    )
    
def query_examples(query, n_results=5):
    u_query_collection=start_chromadb(collection_name="chirho_user_queries_dev6") #to change dynamically on new context creation
    examples_collection=start_chromadb(collection_name="chirho_examples_dev6") #to change dynamically on new context creation
    results=u_query_collection.query(query_texts=[query],
                    n_results=n_results)
    examples_ids=results['ids'][0] 
    examples=examples_collection.get(ids=examples_ids)['documents']
    
    return examples

def convert_manual_examples_to_new_examples_format(manual_examples:list):
    manual_examples_json=[]
    for item in manual_examples:
        code = item[1].replace('Code:','').lstrip()
        if not code.startswith('```') :code='```'+code
        if not code.endswith('```'):code=code+'```'
        manual_examples_json.append({'origination_source_type':'code_file',
                          'origination_source':'chirho_library', #to change dynamically on new context creation
                          'origination_method':'extract_from_library_manual',
                          'code':code, 
                          'description':item[0]})
        
    json.dump(manual_examples_json,open(f'manual_examples.json','w'))
    return manual_examples_json



