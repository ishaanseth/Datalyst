# planner.py (Corrected and updated)

import json
from .config import settings
from .llm import call_llm

def plan_for_question(question_text: str, available_files: list[str]):
    """
    Generate an execution plan for the given question, ensuring only step types
    supported by the executor are used.
    """
    print("Planning for question...")
    print(f"Question text: {question_text}")
    print(f"Available files: {available_files}")

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
You are a planning agent for a data analysis pipeline. Your task is to create a JSON plan to answer the user's question.

The user has provided the following files: {json.dumps(available_files)}
The user's question is:
\"\"\"{question_text}\"\"\"

Create a JSON list of steps to execute. Each step is an object with "id", "type", and "args".

**Rules:**
1.  **Allowed Step Types:** You can ONLY use the following step types: {json.dumps(allowed_types)}.
2.  **File Access:**
    - To read a file provided by the user, use the `read_file` step with the "path" arg set to one of the available files.
    - To use the output of a previous step, the `from` or `df_ref` argument MUST match the `id` of a preceding step.
    - Do NOT invent filenames. All file inputs must come from an available file or a `save_as` from a previous step.
3.  **Step `id`s:** Must be unique, short, and in snake_case.
4.  **`run_python`:** Use this for any custom data processing. The code runs in a directory containing all saved files. It can read and write files.
5.  **Final Answer:** The LAST step MUST be `type: "return"`. Its `from` argument must point to the `id` of the step that produces the final answer.

Example Plan:
[
  {{
    "id": "fetch_wiki_page",
    "type": "fetch_url",
    "args": {{"url": "https://en.wikipedia.org/wiki/List_of_highest-grossing_films", "save_as": "wiki_films.html"}}
  }},
  {{
    "id": "extract_film_table",
    "type": "extract_table",
    "args": {{"from": "fetch_wiki_page", "save_as": "films.csv"}}
  }},
  {{
    "id": "query_films",
    "type": "duckdb_query",
    "args": {{"query": "SELECT Title, \\"Worldwide gross\\" FROM \\"films.csv\\" LIMIT 10;", "save_as": "top_10_films.csv"}}
  }},
  {{
    "id": "final_answer",
    "type": "return",
    "args": {{"from": "query_films"}}
  }}
]

Now, create a complete, valid JSON plan based on the user's question and available files.
Respond ONLY with the raw JSON list of steps. Do not include any explanations or markdown.
"""

    plan_str = call_llm(
        model=settings.DEFAULT_MODEL,
        prompt=prompt,
        max_tokens=2048
    )

    print(f"Raw plan string from LLM:\n{plan_str}")

    try:
        # The LLM sometimes wraps the JSON in ```json ... ```, so we strip it.
        if plan_str.strip().startswith("```json"):
            plan_str = plan_str.strip()[7:-3].strip()
        elif plan_str.strip().startswith("```"):
            plan_str = plan_str.strip()[3:-3].strip()

        plan = json.loads(plan_str)
        print(f"Plan parsed successfully with {len(plan)} steps.")
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON from LLM: {e}")
        raise ValueError(f"Invalid plan JSON: {e}")

    for step in plan:
        stype = step.get("type")
        if stype not in allowed_types:
            raise ValueError(f"Unsupported step type in plan: {stype}")

    print(f"Final parsed plan:\n{json.dumps(plan, indent=2)}")
    return plan
