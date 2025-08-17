# main.py (Final Production Version - Handles any form part name)

import os, json
from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.responses import JSONResponse
from .utils import make_workdir, cleanup_workdir
from .planner import plan_for_question
from .executor import execute_steps
from .config import settings

app = FastAPI(title="TDS Data Analyst Agent")

@app.post("/api") # No trailing slash for robustness
async def analyze(request: Request):
    workdir = make_workdir(settings.WORK_DIR)
    print(f"=== /api/ called ===")
    print(f"Work directory created: {workdir}")

    try:
        # Manually parse the multipart form data
        form_data = await request.form()
        
        qtext = None
        qtext_filename = "questions.txt" # A default name
        available = []

        # --- THIS IS THE NEW ROBUST LOGIC ---
        # Iterate through all uploaded files to find the question file
        for key, file in form_data.items():
            # Check if this is the question file by name
            if key in ["questions", "questions.txt"]:
                qtext_bytes = await file.read()
                qtext = qtext_bytes.decode('utf-8', errors='ignore')
                qtext_filename = file.filename or qtext_filename
                print(f"Found question file in part named '{key}'.")
            else:
                # Treat all other files as attachments
                fpath = os.path.join(workdir, file.filename)
                with open(fpath, "wb") as f: f.write(await file.read())
                available.append(file.filename)
                print(f"Saved attachment: {file.filename}")

        # If no question file was found after checking all parts, raise an error
        if qtext is None:
            raise HTTPException(status_code=422, detail="Request is missing the 'questions' or 'questions.txt' file part.")

        # Save the question text to a file so the planner can see it
        qpath = os.path.join(workdir, qtext_filename)
        with open(qpath, "w", encoding="utf-8") as f:
            f.write(qtext)
        available.insert(0, qtext_filename) # Add it to the front of the list

        print(f"Question text:\n{qtext}")
        print(f"All available files: {available}")

        # --- THE REST OF THE LOGIC IS UNCHANGED ---
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
