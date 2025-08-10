# planner.py (Corrected with a smarter JSON fix)

import json
from .config import settings
from .llm import call_llm

async def plan_for_question(question_text: str, available_files: list[str]):
    print("Planning for question...")
    print(f"Question text: {question_text}")
    print(f"Available files: {available_files}")

    allowed_types = ["fetch_url", "read_file", "extract_table", "duckdb_query", "run_python", "plot", "summarize", "return"]

    prompt = f"""
You are a planning agent for a data analysis pipeline. Your task is to create a JSON plan to answer the user's question.
You are a planning agent... (The rest of your prompt is fine, no need to paste it here again)
The user has provided the following files: {json.dumps(available_files)}
The user's question is:
\"\"\"{question_text}\"\"\"
Create a JSON list of steps to execute. Each step is an object with "id", "type", and "args".
**Rules:**
1.  **Allowed Step Types:** You can ONLY use the following step types: {json.dumps(allowed_types)}.
2.  **File Access:**
    - To read a file provided by the user, use `read_file` with the "path" arg set to one of the available files.
    - To use the output of a previous step, the `from` or `df_ref` argument MUST match the `id` of a preceding step.
    - Do NOT invent filenames. All file inputs must come from an available file or a `save_as` from a previous step.
3.  **Step `id`s:** Must be unique, short, and in snake_case.
4.  **`run_python` Code:** The `code` argument for a `run_python` step is a JSON string. Therefore, all backslashes (\\) and double quotes (") inside the Python code MUST be properly escaped (as \\\\ and \\").
5.  **Final Answer:** The LAST step MUST be `type: "return"`. Its `from` argument must point to the `id` of the step that produces the final answer.
**Example of a full plan:**
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
**Example of a correctly escaped `run_python` step:**
{{
  "id": "clean_data",
  "type": "run_python",
  "args": {{
    "code": "import pandas as pd\\n\\ndf = pd.read_csv('input.csv')\\n# Replace values and save\\ndf['column'] = df['column'].str.replace('old', 'new')\\ndf.to_csv('output.csv', index=False)"
  }}
}}
Now, create a complete, valid JSON plan based on the user's question and available files.
Respond ONLY with the raw JSON list of steps. Do not include any explanations or markdown.
"""

    plan_str = await call_llm(
        model=settings.DEFAULT_MODEL,
        prompt=prompt,
        max_tokens=2048
    )

    print(f"Raw plan string from LLM:\n{plan_str}")

    try:
        if plan_str.strip().startswith("```json"):
            plan_str = plan_str.strip()[7:-3].strip()
        elif plan_str.strip().startswith("```"):
            plan_str = plan_str.strip()[3:-3].strip()
        
        plan = json.loads(plan_str)
        print(f"Plan parsed successfully with {len(plan)} steps.")
    except json.JSONDecodeError as e:
        print(f"Initial JSON parsing failed: {e}. Attempting to fix and re-parse...")
        # --- THIS IS THE NEW, SMARTER FIX ---
        # It targets specific common LLM errors without corrupting the rest of the string.
        try:
            # Fix 1: Remove trailing semicolons in dictionaries
            fixed_plan_str = plan_str.replace('";,', '",').replace('};,', '},')
            
            print("Retrying with fixed semicolons...")
            plan = json.loads(fixed_plan_str)
            print("Plan parsed successfully after fixing semicolons.")
        except Exception as inner_e:
            print(f"ERROR: Could not parse JSON even after attempting to fix it: {inner_e}")
            raise ValueError(f"Invalid plan JSON from LLM, and automatic fixing failed: {inner_e}")

    for step in plan:
        stype = step.get("type")
        if stype not in allowed_types:
            raise ValueError(f"Unsupported step type in plan: {stype}")

    print(f"Final parsed plan:\n{json.dumps(plan, indent=2)}")
    return plan
