# -*- coding: utf-8 -*-
import os
import chromadb
import openai

def start_chromadb(docker=False,collection_name="mira_examples"):

    if docker:
        #Initialize ChromaDB client and create a collection
        client = chromadb.HttpClient(host='localhost', port=8000)
    else:
        chroma_client = chromadb.PersistentClient(path="./chromabd_functions")
    
    collection = chroma_client.get_or_create_collection(name=collection_name)
    
    openai.api_key = os.environ['OPENAI_API_KEY']
    return collection

def add_examples():
    examples=[['User : Can you instantiate an example of a meta-model template?',
               """Assistant: {
               "thought": "I will use my lookup mira tool to lookup_functions related to the meta-model template",
               "tool": "skill_search",
               "tool_input": "meta-model template"
               }""",
               """System:Here are the skills""",
               """Assistant: {
               "thought": "It looks like there are some relevant skills, I will use them to write a function. I will generate code that then tell the user I have done so.",
               "tool": "generate_code",
               "tool_input": "meta-model template"
               }"""],
               ['User : Can you create an SIR model using templates?',
                          """Assistant: {
                          "thought": "I will use my skill_search tool to find functiosn related to creating models and templates to lookup_functions related to the meta-model template",
                          "tool": "skill_search",
                          "tool_input": "creating model using template"
                          }""",
                          """System:Here are the skills""",
                          """Assistant: {
                          "thought": "It looks like there are some relevant skills, I will use them to write a function. I will generate code that then tell the user I have done so.",
                          "tool": "generate_code",
                          "tool_input": "model_template"
                          }"""],
    ]
    user_queries=["Can you instantiate an example of a meta-model template?",'Can you create an SIR model using templates?']
    examples_collection=start_chromadb(collection_name="mira_examples_dev")
    examples_collection.add(
        documents=['\n'.join(example) for example in examples],
        metadatas=[None for i in range(len(examples))], #TODO: add like what example they came from or w/e, maybe how they were made.., maybe add what functions are used..?
        ids=[str(i) for i in range(len(examples))] #make more descriptive?
    )
    #separate index for user queries then just use sim search on query?
    u_query_collection=start_chromadb(collection_name="user_queries_dev")
    u_query_collection.add(
        documents=[u_query for u_query in user_queries],
        metadatas=[None for i in range(len(user_queries))], #TODO: add like what example they came from or w/e, maybe how they were made.., maybe add what functions are used..?
        ids=[str(i) for i in range(len(user_queries))] #make more descriptive?
    )
    
def query_examples(query, n_results=5):
    u_query_collection=start_chromadb(collection_name="user_queries_dev")
    examples_collection=start_chromadb(collection_name="mira_examples_dev")
    results=u_query_collection.query(query_texts=[query],
                    n_results=n_results)
    examples_ids=results['ids'][0] 
    examples=examples_collection.get(ids=examples_ids)['documents']
    
    return examples
    

#TODO: automatic or start generating examples from notebooks, etc..
         
