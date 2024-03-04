# -*- coding: utf-8 -*-
"""
File contains functions to generate system (high level repo level use ) tests and 
submodule (more fine grained tests to do more detailed things in the repo, based on submodules) level tests.
To use this file, first use  create_system_tests and create_submodule_tests (per all submodules you want to test) to generate tests.
Then manually filter them to only include valid tests you care about.
Then run_llm_test on a single example to ensure there are no issues.
Then use run_llm_tests on a dict of tests ({'test':'Do something for me','query_type':'instruction','test_type':'system','tested_object':'library_name'})
"""
from setup_context.example_handling.beaker_agent_proxy.proxy_agent import ProxyAgent 
from setup_context.llm_utils import ask_gpt
from setup_context.example_handling.utils import check_python_code
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

def create_system_tests(library_name="mira"):
    make_examples_base_queries="""
    What are some queries that a user could ask or request they could make to learn more about or use the {library_name} library. 
    Give me 10 examples in the following json format {{'examples':[example1,example2,etc...]}}
    """ 
    #do this with the beaker agent or maybe with some subset of tools??
    make_examples_base_instructions="""
    What are some instructions that a user could give that you could fulfill using the {library_name} library. 
    Give me 10 examples in the following json format {{'examples':[example1,example2,etc...]}}
    """
    agent=ProxyAgent(json.load(open('/media/ssd/recovered_files/beaker-bio/context.json','r')))
    queries_res=agent.react(make_examples_base_queries.format(library_name=library_name))
    instruct_res=agent.react(make_examples_base_queries.format(library_name=library_name))
    return queries_res,instruct_res
    
def create_submodule_tests(submodule_name='mira.metamodel'):
    make_examples_base_instructions="""
    What are some instructions that a user could give that you could make use of the functionality of the {submodule_name} submodule? 
    Give me 10 examples in the following json format {{'examples':[example1,example2,etc...]}}
    """
    agent=ProxyAgent(json.load(open('/media/ssd/recovered_files/beaker-bio/context.json','r')))
    instruct_res=agent.react(make_examples_base_instructions.format(submodule_name=submodule_name))
    return instruct_res

def make_judgement(agent,initial_code_response,query):
    make_judgement="""You have submitted a request to the mira agent, whose purpose is to help you use the {library_name} library. 
    {library_description}
    Your request was : {request}
    The agent's response was : 
    {agent_response}

    Does the agent's response properly fulfill your request and is the code a complete example (not templated, commented stub code)? 
    Please format your response in the following json format - {{"reasoning":why you gave the answer you gave,"answer":[Yes/No]}}
    """
    
    make_judgement2="""You have submitted a request to the mira agent, whose purpose is to help you use the {library_name} library. 
    {library_description}
    Your request was : {request}
    The agent's response was : 
    {agent_response}

    Does the agent's response properly fulfill your request?
    Please format your response in the following json format - {{"reasoning":why you gave the answer you gave,"answer":[Yes/No]}}
    """
    judgement=ask_gpt(make_judgement2.format(agent_response=initial_code_response,request=query,
                                            library_name=agent.library_name,library_description=agent.library_description),
                      model='gpt-4-0125-preview')
    try:
        judgement=json.loads(judgement)
        answer,reasoning=judgement['answer'],judgement['reasoning']
        if type(answer)==list:answer=answer[0]
    except:
        print('Error getting judgement, try again (need to write code for this)')
    return answer,reasoning

#TODO: add error recovery and maybe retrying (maybe retrying is in run_llm_tests)
def run_llm_test(query,query_type='instruction'):
    """
    Takes a query or instruction and tests the context's ability to generate code for that input.
    Allows for up to 3 debugging attempts. 
    Return successful_code or None and trace of actions taken...
    """
    agent=ProxyAgent(json.load(open('/media/ryan/6CD024A87843DD7B/Code/beaker-bio/context.json','r')),use_few_shot=True)
    trace=[]
    
    #if submit code was used test the code, and critique example
    if query_type=="instruction":
        code_writing_portion="Please write code that can be compiled and contains all necessary objects. {query}"
    else:
        code_writing_portion="{query}\nPlease provide a code example that can be compiled and includes of the code necessary to setup the objects required by the example."
    attempts=0
    code_compiled=False
    timer_to_gen_code=0
    try:
        code_response=agent.react(code_writing_portion.format(query=query))
    except Exception as e:
        trace.append({'type':'initial_request','input':code_writing_portion.format(query=query),'output':f'Agent Errored Out : {e}'})
        del agent
        return None,trace
    trace.append({'type':'initial_request','input':code_writing_portion.format(query=query),'output':code_response})
    while attempts<3 and timer_to_gen_code<2:
        timer_to_gen_code=0 
        if code_response.startswith("ProxyAgent.SubmitCode: "):
            code_response=code_response.replace('ProxyAgent.SubmitCode: ','')
            code_compiled,code_output_text=check_python_code(code_response)
            trace.append({'type':'code_compilation_check','input':code_response,'output':(code_compiled,code_output_text)})
            #if res is True, reflect, if not, send debug
            if code_compiled:
                answer,reasoning = make_judgement(agent,code_response,query)
                print(answer,reasoning)
                trace.append({'type':'judgement','input':code_response,'output':(answer,reasoning)})
                if answer=='Yes':
                    print(code_response)
                    del agent
                    return code_response,trace
                else:
                    ask_for_correction="""While the code you gave me did compile properly, it did not fulfill my request as stated.
                    Request - {query}.
                    Here is my reasoning for why your code did not fulfill my request:
                    {reasoning}
                    Please make corrections to your code to fulfill my request.
                    """
                    try:
                        code_response=agent.react(ask_for_correction.format(query=query,reasoning=reasoning))
                    except Exception as e:
                        trace.append({'type':'ask_for_corrections','input':ask_for_correction.format(query=query,reasoning=reasoning),'output':f'Agent Errored Out : {e}'})
                        del agent
                        return None,trace
                    
                    trace.append({'type':'ask_for_corrections','input':ask_for_correction.format(query=query,reasoning=reasoning),'output':code_response})
                    attempts+=1
            else:
                debug_response="""It looks like there was an error with the code you submitted, can you fix it? 
                Here is the traceback : 
                {traceback}""" #do this like x3-x5 or maybe this a good time for LATS.. maybe add some reflection to this prompt
                #debug_response="""It looks like there was an error with the code you submitted, can you fix it? Please reflect on the reason for the error as well as additional information on functions, classes or otherwise that you might need. Then use your tools to get that information. Here is the traceback -{traceback}""" #do this like x3-x5 or maybe this a good time for LATS.. maybe add some reflection to this prompt
                try:
                    code_response=agent.react(debug_response.format(traceback=code_output_text))
                except Exception as e:
                    trace.append({'type':'debug','input':debug_response.format(traceback=code_output_text),'output':f'Agent Errored Out : {e}'})
                    del agent
                    return None,trace
                trace.append({'type':'debug','input':debug_response.format(traceback=code_output_text),'output':code_response})
                attempts+=1
                        
        else:
            while timer_to_gen_code<2: 
                ask_for_code="""Please generate code to do so.""" 
                ask_for_code2=f"""Please generate code to perform my initial request - {query}."""
                try:
                    code_response=agent.react(ask_for_code)
                except Exception as e:
                    trace.append({'type':'ask_for_code','input':ask_for_code,'output':f'Agent Errored Out : {e}'})
                    del agent
                    return None,trace
                trace.append({'type':'ask_for_code','input':ask_for_code,'output':code_response})
                if code_response.startswith("ProxyAgent.SubmitCode: "):
                    attempts+=1
                    continue
                timer_to_gen_code+=1
    del agent
    return None,trace

def run_llm_tests(tests:list,
                  run_initial_check:bool=False,
                  convert_to_examples:bool=True,
                  max_workers:int=4,
                  parallel=False):
    """
    This function performs multiple tests on your context agent at once and returns the results.
    The results can be used to verify system health and/or as new examples for few shot prompting, etc..
    
    Inputs
    ------
    tests List[dict]: A list of dictionaries which describe the tests you would like to run. The keys in the dicts are 
        test (str) : Your request or instruction for the agent
        query_type (str)['instruction'/'query'] : Whether or not your request is a query or instruction
        test_type (str)['system'/'submodule'] : Whether your test tests a submodule or the entire system
        tested_object (str) : The name of the tested library or submodule. Using full tree is best practice (ie mira.metamodel not metamodel..)
        
        ex. [{'test':'Do something for me','query_type':'instruction','test_type':'system','tested_object':'my_library_name'},
             {'test':'Do something different for me','query_type':'query','test_type':'submodule','tested_object':'my_submodule_name'}]
        
    run_initial_check (bool): Whether to run a single test first to ensure tests look correct.
    convert_to_examples(bool): Whether or not to convert successful outputs to and examples json that can be filtered and/or added to dynamic few shot examples.
    max_workers(int): number of tests to run in parallel
    
    example_usage:
            import json
            from setup_handling.example_handling.generate_llm_tests import run_llm_tests
            test_results,new_examples=run_llm_tests([{'test':'Write a SIR model for me','query_type':'instruction','test_type':'system','tested_object':'mira'},
         {'test':'How can I make a SIR model in mira?','query_type':'query','test_type':'submodule','tested_object':'mira.modeling.viz'}])
            json.dump(new_examples,open("new_examples.json",'w'))
    Returns
    -------
    results - list of results for your tests in the same order as the order they were submitted. ie. [results for test 1,results for test 2,etc...]
        each results dict is a tuple with (successful_code_str or None, trace_of_actions) See run_llm_test for more details on what the trace of actions looks like
        ex. [('print("hello world")',[{'type':'initial_request',
                                   'input':"Please write code that can be compiled and contains all necessary objects. Do something for me",
                                   'output':'print("hello world")'},
                                  {'type':'code_compilation_check',
                                   'input':'print("hello world")','output':(True,"hello world"\n)},
                                  trace.append({'type':'judgement','input':'print("hello world")','output':(Yes,'This code does something for me')})]),
             (...same for test2)]
    examples_json : dict of successful tests in example format or None if convert_to_examples is False. Note this dict cuts out all intermediary steps and only creates an example with the request (without the extra helper text) and the successful response.

    """ 
    if run_initial_check:
        print('run single test, get result, pop test from list')
        pass
    examples_json=None 
    results = {}
    if parallel:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(run_llm_test, test['test'],test['query_type']): name for name, test in enumerate(tests)}
            # Setting up tqdm progress bar
            with tqdm(total=len(tests), desc="Performing Tests") as progress:
                for future in as_completed(futures):
                    name = futures[future]
                    try:
                        result = future.result()
                        results[name] = result
                    except Exception as e:
                        print(f"Error processing prompt '{name}': {e}")
                    progress.update(1)  # Update the progress for each completed task
    else:
        for i,test in tqdm(enumerate(tests),desc='Performing Tests'):
            results[i]=run_llm_test(test['test'],test['query_type'])
    if convert_to_examples:
        examples_json=[]
        for key in results.keys():
            if results[key][0] is not None:
                examples_json.append({'origination_source_type':f'test_type_{test["test_type"]}_query_type_{test["test_type"]}',
                                  'origination_source':test["tested_object"],
                                  'origination_method':'llm_tests',
                                  'code':results[key][0], 
                                  'description':test['test']})

    return results,examples_json
    
    
       
    
    
