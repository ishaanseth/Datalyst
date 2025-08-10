import json
import logging
from .settings import settings
from .llm import call_llm

def plan_for_question(question_text: str):
    """
    Generate an execution plan for the given question, ensuring only step types
    supported by the executor are used.
    """
    logging.info("Planning for question...")
    logging.debug("Question text:\n%s", question_text)

    # List of allowed step types (MUST match executor.py exactly)
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

    # Prompt that forces only allowed types
    prompt = f"""
You are a planning agent for a data analysis pipeline.

Given the user's question, create a JSON list of steps to execute. 
Each step must be an object with:
  - "id": short unique name for the step (snake_case)
  - "type": one of {allowed_types}
  - "args": dictionary of parameters for that step
  - Optional: "timeout" in seconds (default 30)

Rules:
- Only use types in {allowed_types}
- For Python code execution, use "type": "run_python" (NOT "python")
- For SQL queries, use "duckdb_query"
- If returning final output to user, use "return" step with "from" pointing to previous step id
- Ensure steps are logically ordered so each one has its dependencies already produced
- Save intermediate outputs using "save_as" in args when relevant

Example plan:
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

Now create a plan for this question:
\"\"\"{question_text}\"\"\"
Respond ONLY with valid JSON list, no explanations.
    """

    # Call the LLM to generate the plan
    plan_str = call_llm(
        model=settings.default_model,
        prompt=prompt,
        max_tokens=1500
    )

    logging.debug("Raw plan string from LLM:\n%s", plan_str)

    try:
        plan = json.loads(plan_str)
        logging.info("Plan parsed successfully with %d steps.", len(plan))
    except json.JSONDecodeError as e:
        logging.error("Invalid JSON from LLM: %s", e)
        raise ValueError(f"Invalid plan JSON: {e}")

    # Final sanity check: ensure only allowed types are present
    for step in plan:
        stype = step.get("type")
        if stype not in allowed_types:
            raise ValueError(f"Unsupported step type in plan: {stype}")

    logging.debug("Final parsed plan:\n%s", json.dumps(plan, indent=2))
    return plan
