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

    # Build the prompt
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

Rules:
- Only use types in {allowed_types}
- For Python code, use "run_python" (NOT "python")
- For SQL queries, use "duckdb_query"
- If returning output, include a "return" step with "from" pointing to prior step's id
- Ensure dependencies are produced before being used
- Save outputs with "save_as" in args when relevant
- Respond ONLY with JSON list, no explanations
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

    # Call the AIPipe API directly
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
    # Adjust this if AIPipe returns in a different format
    plan_str = data["choices"][0]["message"]["content"]

    try:
        plan = json.loads(plan_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid plan JSON: {e}\nRaw output:\n{plan_str}")

    # Sanity check for allowed types
    for step in plan:
        if step.get("type") not in allowed_types:
            raise ValueError(f"Unsupported step type in plan: {step.get('type')}")

    return plan
