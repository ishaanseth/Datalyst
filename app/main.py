# main.py (Final Definitive Version)

import os, json
from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.responses import JSONResponse
from .utils import make_workdir, cleanup_workdir
from .planner import plan_for_question
from .executor import execute_steps
from .config import settings

app = FastAPI(title="TDS Data Analyst Agent")

@app.post("/api")
async def analyze(request: Request):
    workdir = make_workdir(settings.WORK_DIR)
    print(f"=== /api/ called ===")
    
    try:
        form_data = await request.form()
        qtext, available = None, []
        qtext_filename = "questions.txt"

        for key, file in form_data.items():
            if key in ["questions", "questions.txt"]:
                qtext = (await file.read()).decode('utf-8', errors='ignore')
                qtext_filename = file.filename or qtext_filename
            else:
                fpath = os.path.join(workdir, file.filename)
                with open(fpath, "wb") as f: f.write(await file.read())
                available.append(file.filename)
        
        if qtext is None:
            raise HTTPException(status_code=422, detail="Missing 'questions' or 'questions.txt' file part.")

        qpath = os.path.join(workdir, qtext_filename)
        with open(qpath, "w", encoding="utf-8") as f: f.write(qtext)
        available.insert(0, qtext_filename)
        
        print(f"Question text:\n{qtext}")
        print(f"All available files: {available}")

        plan = await plan_for_question(qtext, available)
        results = execute_steps(plan, workdir)

        # --- NEW SIMPLIFIED OUTPUT LOGIC ---
        # The plan now has only one step, and its output is the final answer.
        if not results:
            raise HTTPException(status_code=500, detail="Executor returned no results.")

        # Get the result from the first (and only) step.
        first_step_result = next(iter(results.values()))
        output_str = first_step_result.get("value", "{}")

        try:
            # The output should be a JSON string representing the final object.
            output_json = json.loads(output_str)
        except json.JSONDecodeError:
            # If the script prints something that isn't JSON, return it as a string
            output_json = {"error": "The agent's script did not produce valid JSON.", "output": output_str}

        return JSONResponse(content=output_json)

    finally:
        cleanup_workdir(workdir)
        print(f"Work directory cleaned up.")
