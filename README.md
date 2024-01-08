# beaker-bio

A Beaker context designed for use with biology data and tools. 

## Quickstart

First, add the desired libraries to the `dependencies` within `pyproject.toml`. 

Then, in `context.json` make sure the libraries (as they would be imported) are listed under the `library_names` key. Add a high-level `task_description` that will be used for LLM prompting. 

Then run:

```
export OPENAI_API_KEY=YOUR_KEY_HERE
docker-compose up
```

