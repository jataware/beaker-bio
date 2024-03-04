#Now we need to encode the information from your code and documentation.

#First, to setup the documentation - 
print('Embedding Documentation')
from src.beaker_bio_context.procedures.python3.embed_documents import embed_documents
embed_documents('src/beaker_bio_context/mira/documentation')

#Now we will extract functions and classes from the code - 
print('Embedding Functions and Classes')
from src.beaker_bio_context.procedures.python3.embed_functions_classes_2 import embed_functions_and_classes
embed_functions_and_classes(f'src/beaker_bio_context/mira/code',library_name='mira')

#Now encode the examples - 
print('Embedding Example Code Snippets')
from src.beaker_bio_context.procedures.python3.dynamic_example_selector import add_examples
add_examples()

#Now set the name of the library using  - 
from setup_context.set_names import update_agent_doc_strings
update_agent_doc_strings()
print('Changed References to library - mira')