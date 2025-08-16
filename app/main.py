import os, json
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from .utils import make_workdir, cleanup_workdir
from .planner import plan_for_question
from .executor import execute_steps
from .config import settings

app = FastAPI(title="TDS Data Analyst Agent")

@app.post("/api")
async def analyze(request: Request, questions: UploadFile = File(None), files: list[UploadFile] = File(None)):
    workdir = make_workdir(settings.WORK_DIR)
    print(f"=== /api/ called ===")
    print(f"Work directory created: {workdir}")

    qtext = ""
    available = []
    
    try:
        content_type = request.headers.get('content-type', '')

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

        final = results.get("__final__")
        output = [] # Default to an empty list
        if final and final["type"] == "list":
            output = final["value"]
        
        # --- FINAL POLISH: JSON UNWRAPPING ---
        # If the final output is a list containing a single string that looks like JSON,
        # parse that string to get the actual objects for the final response.
        if isinstance(output, list) and len(output) == 1 and isinstance(output[0], str):
            try:
                # Try to parse the inner string
                parsed_content = json.loads(output[0])
                # If successful, this parsed content becomes the final output
                output = parsed_content
            except json.JSONDecodeError:
                # If parsing fails, it wasn't a JSON string, so we leave it as is.
                pass

        return JSONResponse(content=output)
    finally:
        cleanup_workdir(workdir)
        print(f"Work directory {workdir} cleaned up.")
