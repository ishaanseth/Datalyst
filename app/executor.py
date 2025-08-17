# executor.py (Final Definitive Version)

import subprocess, json, os, shlex, time
from .config import settings

def run_shell(cmd, cwd=None, timeout=30):
    proc = subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True, text=True, timeout=timeout)
    return proc.stdout, proc.stderr, proc.returncode

def execute_steps(steps, workdir):
    results = {}
    start_time = time.time()
    for s in steps:
        if time.time() - start_time > settings.MAX_JOB_SECONDS:
            raise TimeoutError("Job timeout exceeded")
        
        sid, stype, args = s.get("id"), s.get("type"), s.get("args", {})
        
        if stype == "run_python":
            code_lines = args.get("code")
            if not isinstance(code_lines, list):
                raise TypeError("The 'code' for run_python must be a list of strings.")
            
            script_content = "\n".join(code_lines)
            script_path = os.path.join(workdir, f"{sid}.py")
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(script_content)
            
            stdout, stderr, rc = run_shell(f"python {shlex.quote(script_path)}", cwd=workdir, timeout=settings.MAX_JOB_SECONDS - 10)

            if rc != 0:
                print(f"ERROR: Step {sid} failed. STDERR:\n{stderr}")
                raise RuntimeError(f"Execution of python script for '{sid}' failed.")
            
            print(f"Python script for step {sid} executed successfully.")
            results[sid] = {"type": "text", "value": stdout.strip()}
        else:
            raise NotImplementedError(f"Unsupported step type: {stype}")
            
    return results
