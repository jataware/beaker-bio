# -*- coding: utf-8 -*-

import io
import sys
import traceback

def check_python_code(code:str,repl_locals={},repl_modules={}):
    """
    
    Args:
        code (str): The code to run
        
    
    """
    captured_stdout = io.StringIO()
    captured_stderr = io.StringIO()
    original_stdout = sys.stdout
    original_stderr = sys.stderr
    code = '\n'.join([f'import {module}' for module in repl_modules]) +'\n' + code

    traceback_str=''
    print_out='\n'
    try:
        sys.stdout = captured_stdout
        sys.stderr = captured_stderr
        exec(code, repl_locals)
    except Exception as e:
        traceback_str = traceback.format_exc()
        return False, traceback_str
    finally:
        # Always restore stdout and stderr
        sys.stdout = original_stdout
        sys.stderr = original_stderr

    std_out = captured_stdout.getvalue()
    std_err = captured_stderr.getvalue()

    # Optionally handle std_err if you need to capture errors as well
    return True, std_out

