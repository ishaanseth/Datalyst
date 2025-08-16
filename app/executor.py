# executor.py (Definitive Hybrid Toolbox Version)

import subprocess, json, os, shlex, time, duckdb, pandas as pd
import codecs
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
        if elapsed > settings.MAX_JOB_SECONDS: raise TimeoutError("Job timeout exceeded")
        
        sid, stype, args = s.get("id"), s.get("type"), s.get("args", {})
        timeout = s.get("timeout", 30)
        
        print(f"--- EXECUTING STEP: {sid} ({stype}) ---")

        if stype == "fetch_url":
            url = args["url"].rstrip(";")
            save_as = os.path.join(workdir, args.get("save_as", f"{sid}.html"))
            import httpx
            r = httpx.get(url, timeout=timeout)
            with open(save_as, "wb") as f: f.write(r.content)
            results[sid] = {"type": "file", "path": save_as}

        elif stype == "extract_table":
            src = args["from"]
            if src not in results or results[src].get("type") != "file":
                raise ValueError(f"Input step '{src}' for extract_table not found or is not a file.")
            srcpath = results[src]["path"]
            dfs = pd.read_html(srcpath)
            df = dfs[0]
            out = os.path.join(workdir, args.get("save_as", f"{sid}.csv"))
            df.to_csv(out, index=False)
            results[sid] = {"type": "csv", "path": out}

        elif stype == "run_python":
            code_lines = args.get("code")
            if not isinstance(code_lines, list):
                raise TypeError(f"The 'code' for run_python must be a list of strings.")
            
            script_content = "\n".join(code_lines)
            script_path = os.path.join(workdir, f"{sid}.py")
            with open(script_path, "w", encoding="utf-8") as f: f.write(script_content)
            
            stdout, stderr, rc = run_shell(f"python {shlex.quote(script_path)}", cwd=workdir, timeout=timeout)

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
