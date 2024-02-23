#Now we need to encode the information from your code and documentation.

#First, to setup the documentation - 
from src.beaker_bio_context.procedures.python3.embed_documents import embed_documents
embed_documents('src/beaker_bio_context/mira/documentation')

from src.beaker_bio_context.procedures.python3.embed_functions_classes_2 import embed_functions_and_classes
embed_functions_and_classes(f'src/beaker_bio_context/mira/code',library_name='mira')