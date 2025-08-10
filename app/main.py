import os, json
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from .utils import make_workdir, cleanup_workdir
from .planner import plan_for_question
from .executor import execute_steps
from .config import settings

app = FastAPI(title="TDS Data Analyst Agent")

@app.post("/api/")
async def analyze(questions: UploadFile = File(...), files: list[UploadFile] = File(None)):
    print("=== /api/ called ===")
    workdir = make_workdir(getattr(settings, "WORK_DIR", "/tmp"))
    print(f"Work directory created: {workdir}")

    try:
        # Save questions
        qpath = os.path.join(workdir, "questions.txt")
        with open(qpath, "wb") as f:
            f.write(await questions.read())
        print(f"Questions saved to: {qpath}")

        available = ["questions.txt"]

        # Save extra files
        if files:
            for u in files:
                fn = u.filename
                fpath = os.path.join(workdir, fn)
                with open(fpath, "wb") as f:
                    f.write(await u.read())
                available.append(fn)
            print(f"Extra files saved: {available}")

        # Read question text
        with open(qpath, "r", encoding="utf-8", errors="ignore") as f:
            qtext = f.read()
        print(f"Question text:\n{qtext}")

        # Get plan from planner
        print("Calling plan_for_question...")
        plan = plan_for_question(qtext, available)
        print("Plan returned from LLM:\n", json.dumps(plan, indent=2))

        if not isinstance(plan, list):
            raise HTTPException(status_code=500, detail="Planner returned invalid plan")

        # Execute plan
        print("Executing plan...")
        results = execute_steps(plan, workdir)
        print("Execution results:\n", json.dumps(results, indent=2, default=str))

        # If planner declared a return step, use it
        final = results.get("__final__")
        if final:
            if final["type"] == "image":
                answer = final.get("uri")
            elif final["type"] == "csv":
                with open(final["path"], "r", encoding="utf-8") as f:
                    answer = f.read()
            else:
                answer = final.get("value", str(final))
            output = json.loads(answer) if isinstance(answer, str) and answer.strip().startswith("[") else [answer]
        else:
            arr = []
            for s in plan:
                sid = s["id"]
                r = results.get(sid, {})
                if r.get("type") == "image":
                    arr.append(r.get("uri"))
                elif r.get("type") == "csv":
                    with open(r["path"], "r", encoding="utf-8") as f:
                        arr.append(f.read())
                else:
                    arr.append(r.get("value", str(r)))
            output = arr

        print("Final output to return:\n", json.dumps(output, indent=2, default=str))
        return JSONResponse(content=output)

    finally:
        cleanup_workdir(workdir)
        print(f"Work directory {workdir} cleaned up.")
