# executor.py (Final, Simplified Version)

import subprocess, json, os, shlex, time, duckdb, codecs
import pandas as pd
from .utils import image_to_data_uri
from .config import settings

def run_shell(cmd, cwd=None, timeout=30):
    proc = subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True, text=True, timeout=timeout)
    return proc.stdout, proc.stderr, proc.returncode

def execute_steps(steps, workdir):
    results = {}
    start_time = time.time()
    for s in steps:
        elapsed = time.time() - start_time
        if elapsed > settings.MAX_JOB_SECONDS:
            raise TimeoutError("Overall job timeout exceeded")
        
        sid = s.get("id")
        stype = s.get("type")
        args = s.get("args", {})
        timeout = s.get("timeout", 30)
        
        print(f"--- EXECUTING STEP: {sid} ({stype}) ---")

        if stype == "read_file":
            # This tool is still useful if the LLM wants to inspect a file before planning the main script.
            path = os.path.join(workdir, args["path"])
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
            results[sid] = {"type":"text","value":text}

        elif stype == "run_python":
            code_lines = args.get("code")
            
            if not isinstance(code_lines, list):
                raise TypeError(f"The 'code' argument for run_python must be a list of strings, but got {type(code_lines)}")
            
            script_content = "\n".join(code_lines)
            
            script_path = os.path.join(workdir, sid + ".py")
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(script_content)
            
            try:
                stdout, stderr, rc = run_shell(f"python {shlex.quote(script_path)}", cwd=workdir, timeout=timeout)
            except subprocess.TimeoutExpired:
                raise TimeoutError(f"Step {sid} timed out")

            if rc != 0:
                print(f"ERROR: Step {sid} (run_python) failed with return code {rc}.")
                print(f"STDOUT:\n{stdout}")
                print(f"STDERR:\n{stderr}")
                raise RuntimeError(f"Execution of python script for step '{sid}' failed. See logs for details.")
            
            print(f"Python script for step {sid} executed successfully.")
            results[sid] = {"type":"text","value":stdout.strip()}
        
        elif stype == "return":
            from_steps = args.get("from") 
            if not isinstance(from_steps, list):
                from_steps = [from_steps]

            final_result = []
            for step_id in from_steps:
                if step_id in results:
                    result_value = results[step_id].get("value")
                    # Note: We removed the special handling for "image" type here
                    # because all results now come from run_python as text.
                    final_result.append(result_value)
                else:
                    final_result.append(None)
            
            results["__final__"] = {"type": "list", "value": final_result}
        
        else:
            # We raise an error for any tool we no longer support.
            raise NotImplementedError(f"The step type '{stype}' is no longer supported in this simplified executor.")
            
    return results
