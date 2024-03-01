# -*- coding: utf-8 -*-

def update_agent_doc_strings(library_name="mira",submodule_example="mira.modeling",
                             class_example="mira.modeling.triples.Triple",
                             class_method_example="mira.metamodel.template_model.TemplateModel.get_parameters_from_rate_law",
                             function_example="mira.metamodel.io.model_from_json_file",
                             documentation_query_examples='"ode model", "sir model", "using dkg package"',
                             ):
    """
    Replace keywords in a agent docstrings to encourage proper library usage.

    """
    agent_file = './src/beaker_bio_context/agent.py'
    with open(agent_file, 'r', encoding='utf-8') as file:
        content = file.read()

    # Perform all replacements based on the replacements dictionary
    content=content.replace('LIBRARY_NAME',library_name)
    content=content.replace('SUBMODULE_EXAMPLE',submodule_example)
    content=content.replace('CLASS_EXAMPLE',class_example)
    content=content.replace('CLASS_METHOD_EXAMPLE',class_method_example)
    content=content.replace('FUNCTION_EXAMPLE',function_example)
    content=content.replace('DOCUMENTATION_QUERY_EXAMPLES',documentation_query_examples)

    # Write the modified content back to the file
    with open(agent_file, 'w', encoding='utf-8') as file:
        file.write(content)