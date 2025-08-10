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
    workdir = make_workdir(settings.WORK_DIR)
    print(f"=== /api/ called ===")
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

        with open(qpath, "r", encoding="utf-8", errors="ignore") as f:
            qtext = f.read()
        print(f"Question text:\n{qtext}")

        # Get plan from planner (LLM) - THIS IS THE CORRECTED CALL
        plan = await plan_for_question(qtext, available)
        if not isinstance(plan, list):
            raise HTTPException(status_code=500, detail="Planner returned invalid plan")

        # Execute plan
        results = execute_steps(plan, workdir)

        # If planner declared a return step, use it
        final = results.get("__final__")
        output = []
        if final:
            if final["type"] == "image":
                answer = final.get("uri")
                output = [answer]
            elif final["type"] in ["csv", "text", "file"]:
                path = final.get("path")
                if path and os.path.exists(path):
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        answer = f.read()
                else:
                    answer = final.get("value", str(final))

                try:
                    # If the answer is a valid JSON string, parse it
                    parsed_answer = json.loads(answer)
                    output = parsed_answer if isinstance(parsed_answer, list) else [parsed_answer]
                except (json.JSONDecodeError, TypeError):
                    # Otherwise, treat as plain text
                    output = [answer]
            else:
                output = [final.get("value", str(final))]
        else:
            # Fallback: return textual outputs of each step
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

        return JSONResponse(content=output)
    finally:
        cleanup_workdir(workdir)
        print(f"Work directory {workdir} cleaned up.")
