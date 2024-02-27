# beaker-bio

A Beaker context designed for use with mira but designed to be easily generalizable to use new libraries.

## Quickstart

### Mira

If you would like to use the mira library with this code do the following - 
```
python setup_mira.py
```

Then to start the dev notebook run:

```
export OPENAI_API_KEY=YOUR_KEY_HERE
docker-compose up --build
```

On subsequent runs you can drop the build flag.
I would recommend placing the export line to your .bashrc file.

New examples can be added to `mira_manual_examples.json`.

> Once the `chromadb_functions` directory is created it can be zipped and used in `darpa-askem/beaker-kernel`.

### New Library

If you would like to use a new library with this context do the following to set the library up.

First, add the desired libraries to the `dependencies` within `pyproject.toml`. 
Then remove mira install command from the `Dockerfile` -  `RUN pip install git+https://github.com/indralab/mira.git`.
Note, if your installation commands are more complicated you will need to modify the Dockerfile directly to run those commands.

Then, in `context.json` make sure the library name (as it would be imported) is listed under the `library_names` key. 
Add a high-level `task_description` that will be used for LLM prompting.
Add short descriptions of each of the submodules under `library_submodule_descriptions`. 
Then provide a more detailed description of the library as `library_descriptions`. 
Add examples of a submodule name, a class name, a function name,  a class method example and some examples of the kind of queries someone would use to look for functions in your repo (for example for mira we suggest searching for "ode model", "sir model", "using dkg package")

Then add 2 new key value pairs, one a list of the files in your code which contain examples code snippets and one with documentation files which contain examples code snippets per below.
You will add the file names to 2 lists in the the code extracting the examples in the code below - 
Currently context.json is setup to use multiple libraries but this repo only works with a single new repo at a time.
In future updates support for multiple repos will be added.

context.json  - 

    "slug": "beaker_bio", <br>
    "package": "beaker_bio_context.context", <br>
    "class_name": "Context",  <br>
    "library_names": ["mira"], <-- replace this  <br>
    "library_descriptions":["mira is a framework for representing systems using ontology-grounded meta-model templates, \ <br>
    and generating various model implementations and exchange formats from these templates. \  <br>
    It also implements algorithms for assembling and querying domain knowledge graphs in support of modeling."], <-- replace this  <br>
    "library_submodule_descriptions":["mira.dkg - This module contains code for the construction of domain knowledge graphs. \ <br>
    mira.modeling - This module contains code for modeling. The top level contains the Model class, together with the Variable, Transition, and ModelParameter classes, used to represent a Model.\ <br>
    mira.metamodel - This module contains information on code related to meta models.\ <br>
    mira.sources - This module contains code to access models from different sources like json, url, etc..\ <br>
    mira.terarium_client - This module contains code which allows access to the terarium client. A web application for modeling. This module is not to be used.\ <br>
    mira.examples - This module contains examples of how to assemble and modify models in mira."], <--- replace this  <br>
    "class_examples":["mira.modeling.triples.Triple"], <--- replace this <br>
    "function_examples":["mira.metamodel.io.model_from_json_file"], <--- replace this <br>
    "class_method_example":["mira.metamodel.template_model.TemplateModel.get_parameters_from_rate_law"], <--- replace this <br>
    "submodule_examples":["mira.modeling"], <--- replace this <br>
    "documentation_query_examples":["'ode model', 'sir model', 'using dkg package'"], <--- replace this  <br>
    "task_description": "Modeling and Visualization", <--- replace this  <br>
    "doc_files":[["full_path_to_doc_with_example_code_snippet_in_it1","full_path_to_doc_with_example_code_snippet_in_it2",...]], <--- add this key and value
    "code_files":[["full_path_to_code_file_with_example_code_snippet_in_it1","full_path_to_code_file_with_example_code_snippet_in_it2",...]] <--- add this key and value


Then add the code and the documentation under a folder with the library name under src/beaker_bio_context.
Your new directory structure would look like - 

src
...beaker_bio_context
......{library_name}
.........code
.........documentation

Now run the setup script from the top directory

```python
python setup_new_library.py
```

Then to start the dev notebook run:

```
export OPENAI_API_KEY=YOUR_KEY_HERE
docker-compose up --build
```

On subsequent runs you can drop the build flag.
I would recommend placing the export line to your .bashrc file.

