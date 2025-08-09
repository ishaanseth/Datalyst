
# TDS Data Analyst Agent -- Starter Repo

This repository contains a runnable starter for a Data Analyst Agent:
- FastAPI endpoint: `POST /api/` accepting `questions.txt` and optional files.
- Planner stub (call your LLM to produce an executable plan).
- Executor that runs steps safely (subprocess) and returns results.
- Docker + docker-compose example including a sandboxed worker pattern.

**What's included**
- `app/` — FastAPI application and modules.
- `docker/` — Dockerfiles and compose to run app and a sandboxed worker.
- `requirements.txt` — Python dependencies.
- `deploy.md` — deployment notes and security suggestions.

**How to run locally (without Docker)**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**How to run with Docker Compose**
```bash
docker compose up --build
# visit http://localhost:8000/docs
```

**Security notice**
This starter runs arbitrary Python snippets produced by the planner in a subprocess. For production:
- Run the worker in a separate container with strict CPU/memory limits.
- Use OS sandboxing (seccomp, cgroups), or tools like `gVisor`/`firejail`.
- Avoid exposing secrets and carefully validate planner output.

See `deploy.md` for more details.
