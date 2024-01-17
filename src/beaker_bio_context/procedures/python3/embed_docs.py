import inspect
import openai
import pkgutil
import importlib
import os
import chromadb  # Assuming ChromaDB has a Python SDK

from typing import _SpecialGenericAlias

# Initialize ChromaDB client and create a collection
client = chromadb.HttpClient(host='localhost', port=8000)
collection = client.create_collection("python_functions")

openai.api_key = os.environ['OPENAI_API_KEY']

def process_item(module, item, full_name):
    library_base_path = os.path.dirname(inspect.getfile(module))  # Get the base path of the library
    try:
        # Check if the item's file path starts with the library's base path
        item_file_path = inspect.getfile(item)
        if not item_file_path.startswith(library_base_path):
            print(f"Skipping {full_name}: Not part of the library.")
            return

        docstring = item.__doc__ or ''
        source_code = inspect.getsource(item)

        expanded_description = get_expanded_description(full_name, docstring, source_code)

        # Add to ChromaDB collection
        collection.add(
            documents=[expanded_description],
            metadatas=[{"function_name": full_name, "docstring": docstring, "source_code": source_code}],
            ids=[full_name]
        )
    except Exception as e:
        print(f"Skipping {full_name}: {e}")

def process_submodule(module, submodule):
    for attribute_name in dir(submodule):
        if attribute_name.startswith('_'):
            continue

        attribute = getattr(submodule, attribute_name)
        full_name = f"{submodule.__name__}.{attribute_name}"
        print(f"Processing {full_name}")

        # Check if attribute is a function, method, class, and not a _SpecialGenericAlias
        if not isinstance(attribute, _SpecialGenericAlias):
            if inspect.isfunction(attribute) or inspect.ismethod(attribute) or inspect.isclass(attribute):
                process_item(module, attribute, full_name)
                if inspect.isclass(attribute):
                    # Optionally process methods within the class
                    process_class_methods(module, attribute, full_name)

def process_class_methods(module, cls, class_full_name):
    for method_name in dir(cls):
        if method_name.startswith('_'):
            continue

        method = getattr(cls, method_name)
        if inspect.isfunction(method) or inspect.ismethod(method):
            process_item(module, method, f"{class_full_name}.{method_name}")

def get_docstrings(module):
    if hasattr(module, '__path__'):  # It's a package
        for importer, modname, ispkg in pkgutil.walk_packages(module.__path__, prefix=module.__name__ + "."):
            try:
                # Load the submodule
                print(f"#### Processing submodule {modname}")
                submodule = importlib.import_module(modname)
                process_submodule(module, submodule)
            except Exception as e:
                print(f"{modname}: {e}")
                # Skip modules that can't be imported
                continue
    else:  # It's a single module
        process_submodule(module, module)

def get_expanded_description(func_name, docstring, source_code):
    prompt = f"Explain the function '{func_name}' with its docstring '{docstring}' and source code:\n{source_code}\nIn simple terms:"
    # token_limit = 16385
    token_limit = 7500 # setting below real threshold since tokenizer is "dumb" and isn't conservative enough
    completion = openai.chat.completions.create(
        model="gpt-3.5-turbo-1106",
        messages=[
            {
                "role": "user",
                "content": truncate_to_token_limit(prompt, token_limit),
            },
        ],
    )
    return completion.choices[0].message.content


def truncate_to_token_limit(text, token_limit):
    # Split the text into tokens (words)
    tokens = text.split()

    # Ensure the number of tokens does not exceed the limit
    if len(tokens) <= token_limit:
        return text
    else:
        # Join tokens back into a string, without exceeding the token limit
        print("Truncating prompt...")
        truncated_text = ' '.join(tokens[:token_limit])
        return truncated_text


def query_function(query, n_results=2):
    # Query the ChromaDB collection
    result = collection.query(
        query_texts=[query],
        n_results=n_results
    )
    cleaned_results = {}
    for i in range(len(result['ids'][0])):
        func = result['ids'][0][i]
        description = result['documents'][0][i]
        docstring = result['metadatas'][0][i]['docstring']
        cleaned_results[func] = {'description': description, 'docstring': docstring}

    return cleaned_results


# Example usage
import mira.modeling.viz
get_docstrings(mira.modeling.viz)  # Process a library
res = query_function("stratify")
res