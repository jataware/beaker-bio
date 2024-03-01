# -*- coding: utf-8 -*-
import openai
import time
import tiktoken
from concurrent.futures import ThreadPoolExecutor, as_completed
import tenacity
from functools import wraps
from tqdm import tqdm

def retry_decorator(retry_count=5, delay_seconds=10):
    """A decorator for retrying a function call with a specified delay and retry count."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(retry_count):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    print(f"Attempt {attempt + 1} failed with error: {e}")
                    if attempt < retry_count - 1:
                        time.sleep(delay_seconds)
            raise Exception(f"All {retry_count} attempts failed")
        return wrapper
    return decorator

def check_and_trim_tokens(prompt, model):
    encoding = tiktoken.get_encoding("cl100k_base")
    max_length_dict = {
        'gpt-3.5-turbo-0125': 16385,
        'gpt-4-0125-preview':128000, #max tokens out is 4096
        "text-embedding-ada-002":8192,
    }
    max_tokens = max_length_dict[model]
    tokens=encoding.encode(prompt)
    if len(tokens) > max_tokens:
        print(f"Trimming prompt from {len(tokens)} characters to fit within token limit.")
        return encoding.decode(tokens[:max_tokens])
    return prompt
       
@retry_decorator(retry_count=3, delay_seconds=5)
def ask_gpt(prompt, model="gpt-3.5-turbo-0125",**kwargs):
    """Send a prompt to GPT and get a response."""
    checked_prompt = check_and_trim_tokens(prompt, model)
    response = openai.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": checked_prompt}
        ],
        **kwargs
    )
    return response.choices[0].message.content.strip()
        
def process_ask_gpt_in_parallel(prompts, prompt_names, max_workers=8, model="gpt-3.5-turbo-1106",**kwargs):
    results = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(ask_gpt, prompt, model,**kwargs): name for prompt, name in zip(prompts, prompt_names)}
        # Setting up tqdm progress bar
        with tqdm(total=len(prompts), desc="Processing Prompts") as progress:
            for future in as_completed(futures):
                name = futures[future]
                try:
                    result = future.result()
                    results[name] = result
                except Exception as e:
                    print(f"Error processing prompt '{name}': {e}")
                progress.update(1)  # Update the progress for each completed task
    return results

