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
        #chroma_client = chromadb.PersistentClient(path="./chromabd_functions")
    
    collection = chroma_client.get_or_create_collection(name=collection_name)
    
    openai.api_key = os.environ['OPENAI_API_KEY']
    return collection
#TODO: change example format to the same as what the agent will see?
#TODO: change examples to conversations?
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
           ['Generate a sir model and then create an ode model from that model',
            """Code : ```import numpy
import matplotlib.pyplot as plt

from mira.metamodel import *
from mira.modeling import Model
from mira.modeling.ode import OdeModel, simulate_ode_model
template_model = TemplateModel(
    templates=[
        NaturalConversion(
            subject=Concept(name='infected'),
            outcome=Concept(name='recovered')
        ),
        ControlledConversion(
            subject=Concept(name='susceptible'),
            outcome=Concept(name='infected'),
            controller=Concept(name='infected')
        )
    ]
)
model = Model(template_model)
ode_model = OdeModel(model)```"""],
['simulate my model ode_model using some default conditions then plot the results',
 """Code : ```times = numpy.linspace(0, 25, 100)

res = simulate_ode_model(
    ode_model=ode_model,
    initials=numpy.array([0.01, 0, 0.99]),
    parameters={('infected', 'recovered', 'NaturalConversion', 'rate'): 0.5,
                ('susceptible', 'infected', 'infected', 'ControlledConversion', 'rate'): 1.1},
    times=times
)
infected, recovered, susceptible = plt.plot(times, res)
infected.set_color('blue')
recovered.set_color('orange')
susceptible.set_color('green')
plt.show()```"""],
['Get template model "BIOMD0000000956"',
 """Code : ```from mira.sources.biomodels import get_template_model
 template_model = get_template_model('BIOMD0000000956')```"""],
 ['Stratify my sir template model by 2 different cities',
  """Code : ```import requests
  sir_template_model_dict = sir_template_model.dict()
  rest_url = "http://34.230.33.149:8771"
  res = requests.post(rest_url + "/api/stratify", json={"template_model": sir_template_model_dict, "key": "city", "strata": ["Boston", "New York City"]})
print(res.json())```"""],
['Create a SIR model',
 """Code : ```import requests
from mira.metamodel import Concept, ControlledConversion, NaturalConversion, TemplateModel

# Example TemplateModel
infected = Concept(name="infected population", identifiers={"ido": "0000511"})
susceptible = Concept(name="susceptible population", identifiers={"ido": "0000514"})
immune = Concept(name="immune population", identifiers={"ido": "0000592"})
controlled_conversion = ControlledConversion(
    controller=infected,
    subject=susceptible,
    outcome=infected,
)
natural_conversion = NaturalConversion(subject=infected, outcome=immune)
sir_template_model = TemplateModel(templates=[controlled_conversion, natural_conversion])
sir_template_model_dict = sir_template_model.dict()
print(sir_template_model.json())```""",
"Convert my model to a petrinet",
"""Code : ```import requests
rest_url = "http://34.230.33.149:8771"
res = requests.post(rest_url + "/api/to_petrinet", json=sir_template_model_dict)
print(res.json())```"""]
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
         
