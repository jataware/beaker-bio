import chromadb

def query_functions(query, n_results=5):
    '''
    Takes in a query and returns the top n results in the following form:

    {'function_name': {
                        'description': 'description of the function here',
                        'docstring': 'the docstring of the function here'
                        },
    ...
    }
    '''
    client = chromadb.HttpClient(host='chromadb', port=8000)
    collection = client.get_collection("python_functions")
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

query_functions("{{query}}")