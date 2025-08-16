# main (2).py (Now handles both multipart and raw-body requests)

import os, json
from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.responses import JSONResponse
from .utils import make_workdir, cleanup_workdir
from .planner import plan_for_question
from .executor import execute_steps
from .config import settings

app = FastAPI(title="TDS Data Analyst Agent")

@app.post("/api") # No trailing slash for robustness
async def analyze(request: Request, questions: UploadFile = File(None), files: list[UploadFile] = File(None)):
    workdir = make_workdir(settings.WORK_DIR)
    print(f"=== /api/ called ===")
    print(f"Work directory created: {workdir}")
    
    qtext = ""
    available = []

    try:
        content_type = request.headers.get('content-type', '')

        # --- THIS IS THE NEW LOGIC ---
        # Check if the request is multipart (like from your curl command)
        if 'multipart/form-data' in content_type:
            print("Processing multipart/form-data request.")
            if not questions:
                raise HTTPException(status_code=422, detail="Multipart request missing 'questions' file.")
            
            qtext_bytes = await questions.read()
            qtext = qtext_bytes.decode('utf-8', errors='ignore')
            available.append(questions.filename or "questions.txt")

            if files:
                for u in files:
                    fpath = os.path.join(workdir, u.filename)
                    with open(fpath, "wb") as f: f.write(await u.read())
                    available.append(u.filename)

        # Else, assume the request body is the raw question text (like from the evaluator)
        else:
            print("Processing raw-body request.")
            qtext_bytes = await request.body()
            qtext = qtext_bytes.decode('utf-8', errors='ignore')
            available.append("questions.txt") # The evaluator provides the questions file
            # In this mode, we assume the other necessary files (e.g., edges.csv) are also sent
            # The promptfoo config will handle sending multiple files if needed

        # Save the question text to a file so the planner can see it
        qpath = os.path.join(workdir, "questions.txt")
        with open(qpath, "w", encoding="utf-8") as f:
            f.write(qtext)
        
        print(f"Question text:\n{qtext}")

        # --- THE REST OF THE LOGIC IS THE SAME ---
        plan = await plan_for_question(qtext, available)
        if not isinstance(plan, list):
            raise HTTPException(status_code=500, detail="Planner returned invalid plan")

        results = execute_steps(plan, workdir)

        final = results.get("__final__")
        output = []
        if final and final["type"] == "list":
            output = final["value"]
        
        if isinstance(output, list) and len(output) == 1 and isinstance(output[0], str):
            try:
                parsed_content = json.loads(output[0])
                output = parsed_content
            except json.JSONDecodeError:
                pass

        return JSONResponse(content=output)
    finally:
        cleanup_workdir(workdir)
        print(f"Work directory {workdir} cleaned up.")
