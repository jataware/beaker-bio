# -*- coding: utf-8 -*-
import os
import chromadb
import openai

def start_chromadb(docker=False,collection_name="mira_examples"):

    if docker:
        #Initialize ChromaDB client and create a collection
        client = chromadb.HttpClient(host='localhost', port=8000)
    else:
        chroma_client = chromadb.PersistentClient(path="/bio_context/chromabd_functions")
    
    collection = chroma_client.get_or_create_collection(name=collection_name)
    
    openai.api_key = os.environ['OPENAI_API_KEY']
    return collection

def add_examples():
    examples=[['Can you instantiate a SIR model using the metamodel template?',
"""Code : ```from mira.metamodel import ControlledConversion, NaturalConversion, Concept, Template

         infected = Concept(name='infected population', identifiers={'ido': '0000511'})
         susceptible = Concept(name='susceptible population', identifiers={'ido': '0000514'})
         immune = Concept(name='immune population', identifiers={'ido': '0000592'})
         
         t1 = ControlledConversion(
             controller=infected,
             subject=susceptible,
             outcome=infected,
         )
         t2 = NaturalConversion(subject=infected, outcome=immune)
         Template.from_json(t1.dict())
         from mira.metamodel import TemplateModel
         sir_model = TemplateModel(templates=[t1, t2])```
 """],
               ['Create a more complicated SIRD style model using templates',
"""Code : ```from mira.metamodel import ControlledConversion, NaturalConversion, Concept, Template
exposed = Concept(name='exposed population', identifiers={'genepio': '0001538'})
  deceased = Concept(name='deceased population', identifiers={'ncit': 'C28554'})
  s1 = ControlledConversion(
      controller=infected,
      subject=susceptible,
      outcome=exposed
  )
  s2 = NaturalConversion(
      subject=exposed,
      outcome=infected
  )
  s3 = NaturalConversion(
      subject=infected,
      outcome=deceased
  )
  M1 = TemplateModel(templates=[s1, s2, s3, t2])
  t2 = NaturalConversion(subject=infected, outcome=immune)
  u1 = ControlledConversion(
      controller=exposed,
      subject=susceptible,
      outcome=exposed
  )
  M2 = TemplateModel(templates=M1.templates + [u1])
  unreported = Concept(name='immune unreported population', identifiers={'ido': '0000592'},
                       context={'status': 'unreported'})
  
  v1 = NaturalConversion(
      subject=exposed,
      outcome=unreported
  )
  M3 = TemplateModel(templates=M2.templates + [v1])
  w1 = NaturalConversion(
      subject=immune,
      outcome=susceptible
  )
  M4 = TemplateModel(templates=M2.templates + [w1])
  TemplateModel.from_json(M4.dict())```
           """],
    ]
    user_queries=[ex[0] for ex in examples]
    examples_collection=start_chromadb(collection_name="mira_examples_dev1")
    examples_collection.add(
        documents=['Request: ' + '\n'.join(example) for example in examples],
        metadatas=[None for i in range(len(examples))], #TODO: add like what example they came from or w/e, maybe how they were made.., maybe add what functions are used..?
        ids=[str(i) for i in range(len(examples))] #make more descriptive?
    )
    #separate index for user queries then just use sim search on query?
    u_query_collection=start_chromadb(collection_name="user_queries_dev1")
    u_query_collection.add(
        documents=[u_query for u_query in user_queries],
        metadatas=[None for i in range(len(user_queries))], #TODO: add like what example they came from or w/e, maybe how they were made.., maybe add what functions are used..?
        ids=[str(i) for i in range(len(user_queries))] #make more descriptive?
    )
    
def query_examples(query, n_results=5):
    u_query_collection=start_chromadb(collection_name="user_queries_dev1")
    examples_collection=start_chromadb(collection_name="mira_examples_dev1")
    results=u_query_collection.query(query_texts=[query],
                    n_results=n_results)
    examples_ids=results['ids'][0] 
    examples=examples_collection.get(ids=examples_ids)['documents']
    
    return examples
    

#TODO: automatic or start generating examples from notebooks, etc..
         
