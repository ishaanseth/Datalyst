
import os, shutil, base64, uuid

def make_workdir(base="/tmp/tda_jobs"):
    job_id = uuid.uuid4().hex
    path = os.path.join(base, job_id)
    os.makedirs(path, exist_ok=True)
    return path

def cleanup_workdir(path):
    try:
        shutil.rmtree(path)
    except Exception:
        pass

def image_to_data_uri(path, mime="image/png"):
    with open(path, "rb") as f:
        import base64
        data = base64.b64encode(f.read()).decode()
    return f"data:{mime};base64,{data}"
