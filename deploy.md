
# Deployment & Security Notes

## Overview
This starter uses a planner (LLM) -> executor (app) model. The app runs code produced by the planner. This is powerful but dangerous.

## Recommendations
1. **Isolation**: Run executor/workers in separate containers, not the same process as the web server.
2. **Resource limits**: Use Docker resource limits (memory/cpu) and timeouts on subprocess calls.
3. **Network controls**: Restrict outbound network from worker containers (if not needed).
4. **Authentication**: Protect API endpoint with API keys or OAuth.
5. **Validation**: Validate planner JSON strictly (only allow approved step types).
6. **Logging**: Stream logs to a central logging system and rotate logs.

## Sandboxed worker pattern (suggested)
- `web` service (FastAPI) only accepts requests and stores files.
- `worker` service consumes job queue (Redis/RabbitMQ) and executes plans inside a constrained container.
- Use Docker Compose to run both locally, and move to a more secure host for production (Kubernetes with PSPs, etc).
