
import subprocess, json, os, shlex, time, duckdb, pandas as pd
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
        if stype == "fetch_url":
            import httpx
            url = args["url"]
            save_as = os.path.join(workdir, args.get("save_as", sid + ".html"))
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
            df = con.execute(query).df()
            out = os.path.join(workdir, args.get("save_as", sid + ".csv"))
            df.to_csv(out, index=False)
            results[sid] = {"type":"csv","path":out}
        elif stype == "run_python":
            code = args["code"]
            script_path = os.path.join(workdir, sid + ".py")
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(code)
            try:
                stdout, stderr, rc = run_shell(f"python {shlex.quote(script_path)}", cwd=workdir, timeout=timeout)
            except subprocess.TimeoutExpired:
                raise TimeoutError(f"Step {sid} timed out")
            results[sid] = {"type":"process","stdout":stdout,"stderr":stderr,"rc":rc}
        elif stype == "plot":
            df_ref = args["df_ref"]
            if df_ref not in results:
                raise ValueError("df_ref not found")
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
        elif stype == "summarize":
            from_steps = args.get("from_steps", [])
            collected = ""
            for fs in from_steps:
                r = results.get(fs)
                if not r: continue
                if r.get("type") == "text":
                    collected += r.get("value","") + "\n"
                elif r.get("type") == "csv":
                    collected += f"[CSV at {r.get('path')}]\n"
                else:
                    collected += str(r) + "\n"
            results[sid] = {"type":"text","value":collected}
        elif stype == "return":
            src = args.get("from")
            results["__final__"] = results.get(src, {"type":"text","value":"(missing)"})
        else:
            raise NotImplementedError(f"Unknown step type {stype}")
    return results
