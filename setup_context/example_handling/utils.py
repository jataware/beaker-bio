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
    sys.stdout = captured_stdout
    sys.stderr = captured_stderr
    code = '\n'.join([f'import {module}' for module in repl_modules]) +'\n' + code

    traceback_str=''
    print_out='\n'
    try:
        exec(code, repl_locals)
        # restore stdout/stderr
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
        std_out,std_err=captured_stdout.getvalue(), captured_stderr.getvalue()
        return True,std_out
    except Exception as e:
        traceback_str = traceback.format_exc()
        return False, traceback_str

