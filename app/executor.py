# executor.py (Final Definitive Version)

import subprocess, json, os, shlex, time, pandas as pd
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
        
        print(f"--- EXECUTING STEP: {sid} ({stype}) ---")

        if stype == "fetch_url":
            import httpx
            url = args["url"].rstrip(";")
            save_as = os.path.join(workdir, args.get("save_as", f"{sid}.html"))
            r = httpx.get(url, timeout=30)
            with open(save_as, "wb") as f: f.write(r.content)
            results[sid] = {"type": "file", "path": save_as}

        elif stype == "extract_table":
            src_id = args["from"]
            if src_id not in results or results[src_id].get("type") != "file":
                raise ValueError(f"Input step '{src_id}' for extract_table not found or is not a file.")
            src_path = results[src_id]["path"]
            df = pd.read_html(src_path)[0]
            save_as = os.path.join(workdir, args.get("save_as", f"{sid}.csv"))
            df.to_csv(save_as, index=False)
            results[sid] = {"type": "csv", "path": save_as}

        elif stype == "run_python":
            code_lines = args.get("code")
            if not isinstance(code_lines, list):
                raise TypeError("The 'code' for run_python must be a list of strings.")
            
            script_content = "\n".join(code_lines)
            script_path = os.path.join(workdir, f"{sid}.py")
            with open(script_path, "w", encoding="utf-8") as f: f.write(script_content)
            
            stdout, stderr, rc = run_shell(f"python {shlex.quote(script_path)}", cwd=workdir, timeout=settings.MAX_JOB_SECONDS - 10)

            if rc != 0:
                print(f"ERROR: Step {sid} failed. STDERR:\n{stderr}")
                raise RuntimeError(f"Execution of python script for '{sid}' failed.")
            
            print(f"Python script for step {sid} executed successfully.")
            results[sid] = {"type": "text", "value": stdout.strip()}
        
        elif stype == "return":
            from_steps = args.get("from", [])
            if not isinstance(from_steps, list): from_steps = [from_steps]

            final_result = []
            for step_id in from_steps:
                final_result.append(results.get(step_id, {}).get("value"))
            
            results["__final__"] = {"type": "list", "value": final_result}
        
        else:
            raise NotImplementedError(f"Unsupported step type: {stype}")
            
    return results
