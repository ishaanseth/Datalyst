import json
import requests
from .config import settings

def plan_for_question(question_text: str, available_files=None):
    """
    Generate an execution plan for the given question using AIPipe API,
    ensuring only step types supported by executor.py are used.
    """
    if not settings.AIPIPE_TOKEN:
        raise ValueError("AIPIPE_TOKEN environment variable not set.")

    allowed_types = [
        "fetch_url",
        "read_file",
        "extract_table",
        "duckdb_query",
        "run_python",
        "plot",
        "summarize",
        "return"
    ]

    prompt = f"""
You are a planning agent for a data analysis pipeline.

User has asked the following question and provided these files:
Question:
\"\"\"{question_text}\"\"\"

Files available:
{available_files or []}

Create a JSON list of steps to execute.
Each step must have:
  - "id": short unique snake_case name
  - "type": one of {allowed_types}
  - "args": dictionary of parameters for that step
  - Optional: "timeout" (default 30)

**CRITICAL RULES:**
1. Only use types in {allowed_types}.
2. For Python code execution, use "run_python" (NOT "python").
3. For SQL queries, use "duckdb_query".
4. If returning output, include a "return" step with "from" pointing to a prior step's id.
5. Ensure dependencies are produced before being used.
6. **If a step writes an output file that will be used later, include `"save_as"` in "args" with the exact filename written.**
7. Any later step must reference previous outputs using `"from": "<step_id>"`, not `"path"`.
8. Do not hardcode file paths in later steps—always use `"from"` to chain outputs.
9. Always ensure the filename in `"save_as"` matches exactly what the code writes to disk.
10. Respond ONLY with a valid JSON list, no explanations.

Example:
[
  {{
    "id": "read_wiki",
    "type": "fetch_url",
    "args": {{"url": "https://example.com", "save_as": "wiki.html"}}
  }},
  {{
    "id": "table",
    "type": "extract_table",
    "args": {{"from": "read_wiki", "save_as": "table.csv"}}
  }},
  {{
    "id": "answer",
    "type": "return",
    "args": {{"from": "table"}}
  }}
]
    """

    headers = {
        "Authorization": f"Bearer {settings.AIPIPE_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": settings.DEFAULT_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1500
    }
    resp = requests.post(f"{settings.AIPIPE_API_BASE}/chat/completions", headers=headers, json=payload)
    resp.raise_for_status()

    data = resp.json()
    plan_str = data["choices"][0]["message"]["content"]

    try:
        plan = json.loads(plan_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid plan JSON: {e}\nRaw output:\n{plan_str}")

    for step in plan:
        if step.get("type") not in allowed_types:
            raise ValueError(f"Unsupported step type in plan: {step.get('type')}")

    return plan
