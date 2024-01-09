import inspect
import openai
import pkgutil
import importlib
import os
import chromadb  # Assuming ChromaDB has a Python SDK

# Initialize ChromaDB client and create a collection
client = chromadb.Client()
collection = client.create_collection("python_functions")

openai.api_key = os.environ['OPENAI_API_KEY']


def get_docstrings(module):
    result = {}
    prefix = module.__name__ + "."

    for importer, modname, ispkg in pkgutil.walk_packages(module.__path__, prefix):
        try:
            # Load the submodule
            submodule = importlib.import_module(modname)
            # Process the submodule
            for attribute_name in dir(submodule):
                if attribute_name.startswith('_'):
                    continue

                attribute = getattr(submodule, attribute_name)
                full_name = f"{modname}.{attribute_name}"

                if hasattr(attribute, '__doc__') and callable(attribute):
                    docstring = attribute.__doc__ or ''
                    source_code = inspect.getsource(attribute)
                    expanded_description = get_expanded_description(full_name, docstring, source_code)

                    # Add to ChromaDB collection
                    collection.add(
                        documents=[expanded_description],
                        metadatas=[{"function_name": full_name, "docstring": docstring, "source_code": source_code}],
                        ids=[full_name]
                    )
        except Exception as e:
            print(e)
            # Skip modules that can't be imported
            continue

    return result


def get_expanded_description(func_name, docstring, source_code):
    print(f"Explaining function: {func_name}")
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


def query_function(query_text, n_results=6):
    # Query the ChromaDB collection
    results = collection.query(
        query_texts=[query_text],
        n_results=n_results
    )
    return results


# Example usage
import Bio
get_docstrings(Bio)  # Process a library
result = query_function("align")