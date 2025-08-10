# executor.py (Final Completed Version)

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
        if elapsed > settings.MAX_JOB_SECONDS:
            raise TimeoutError("Overall job timeout exceeded")
        sid = s.get("id")
        stype = s.get("type")
        args = s.get("args", {})
        timeout = s.get("timeout", 30)
        
        print(f"--- EXECUTING STEP: {sid} ({stype}) ---")

        if stype == "fetch_url":
            url = args["url"].rstrip(";")
            save_as = os.path.join(workdir, args.get("save_as", sid + ".html"))
            import httpx
            r = httpx.get(url, timeout=timeout)
            with open(save_as, "wb") as f:
                f.write(r.content)
            results[sid] = {"type":"file","path":save_as}
        elif stype == "read_file":
            path = os.path.join(workdir, args["path"])
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
            results[sid] = {"type":"text","value":text}
        elif stype == "extract_table":
            src = args["from"]
            if src in results and results[src]["type"]=="file":
                srcpath = results[src]["path"]
            else:
                srcpath = os.path.join(workdir, src)
            dfs = pd.read_html(srcpath)
            df = dfs[0]
            out = os.path.join(workdir, args.get("save_as", sid + ".csv"))
            df.to_csv(out, index=False)
            results[sid] = {"type":"csv","path":out}
        elif stype == "duckdb_query":
            query = args["query"]
            con = duckdb.connect()
            con.execute(f"SET FILE_SEARCH_PATH='{workdir}'")
            df = con.execute(query).df()
            out = os.path.join(workdir, args.get("save_as", sid + ".csv"))
            df.to_csv(out, index=False)
            results[sid] = {"type":"csv","path":out}
        elif stype == "run_python":
            code_lines = args.get("code")
            
            # --- THIS IS THE NEW LOGIC ---
            if not isinstance(code_lines, list):
                raise TypeError(f"The 'code' argument for run_python must be a list of strings, but got {type(code_lines)}")
            
            # Join the lines of code into a single script
            script_content = "\n".join(code_lines)
            
            script_path = os.path.join(workdir, sid + ".py")
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(script_content) # Write the combined script
            
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
            # The stdout of the script is its result
            results[sid] = {"type":"text","value":stdout.strip()}
        
        # --- THIS IS THE COMPLETED FEATURE ---
        elif stype == "summarize":
            print("Summarizing data...")
            src_id = args.get("from")
            if not src_id or src_id not in results or results[src_id].get("type") != "csv":
                raise ValueError(f"Invalid 'from' reference for summarize step: {src_id}")
            
            csv_path = results[src_id]["path"]
            df = pd.read_csv(csv_path)

            columns = args.get("columns")
            if columns and isinstance(columns, list):
                existing_cols = [col for col in columns if col in df.columns]
                df = df[existing_cols]

            max_rows = args.get("max_rows") or args.get("top_n")
            if max_rows and isinstance(max_rows, int):
                df = df.head(max_rows)
            
            summary_json = df.to_json(orient='records', indent=2)
            results[sid] = {"type": "text", "value": summary_json}
            
        elif stype == "plot":
            df_ref = args["df_ref"]
            if df_ref not in results: raise ValueError("df_ref not found")
            csv_path = results[df_ref]["path"]
            df = pd.read_csv(csv_path)
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            fig, ax = plt.subplots(figsize=(6,4))
            ax.scatter(df[args["x"]], df[args["y"]])
            if args.get("regression"):
                import numpy as np
                x = df[args["x"]].astype(float)
                y = df[args["y"]].astype(float)
                m, b = np.polyfit(x, y, 1)
                xs = np.linspace(x.min(), x.max(), 100)
                ax.plot(xs, m*xs + b, linestyle='--', color='red')
            ax.set_xlabel(args.get("xlabel", args["x"]))
            ax.set_ylabel(args.get("ylabel", args["y"]))
            out = os.path.join(workdir, args.get("save_as", sid + ".png"))
            fig.savefig(out, bbox_inches='tight', dpi=90)
            plt.close(fig)
            results[sid] = {"type":"image","path":out, "uri": image_to_data_uri(out, mime='image/png')}
        elif stype == "return":
            # The 'from' arg should now be a list of step IDs
            from_steps = args.get("from") 
            if not isinstance(from_steps, list):
                # Handle the old way for backward compatibility, but log a warning
                print("WARNING: 'from' in return step should be a list. Treating as single item.")
                from_steps = [from_steps]

            final_result = []
            for step_id in from_steps:
                if step_id in results:
                    # Append the value of the step to our final list
                    result_value = results[step_id].get("value")
                    if results[step_id].get("type") == "image":
                        result_value = results[step_id].get("uri")
                    final_result.append(result_value)
                else:
                    final_result.append(None) # Add a placeholder if a step is missing
            
            # This special key now holds a list of the final results
            results["__final__"] = {"type": "list", "value": final_result}
        else:
            raise NotImplementedError(f"Unknown step type {stype}")
    return results
