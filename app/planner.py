# planner.py (Using a list of strings for code to simplify the LLM's task)

import json
from .config import settings
from .llm import call_llm

async def plan_for_question(question_text: str, available_files: list[str]):
    print("Planning for question...")
    print(f"Question text: {question_text}")
    print(f"Available files: {available_files}")

    allowed_types = ["fetch_url", "read_file", "extract_table", "duckdb_query", "run_python", "plot", "summarize", "return"]

    # The prompt now enforces that the 'code' argument is a list of strings.
    prompt = f"""
You are a planning agent for a data analysis pipeline. You create a plan to answer the user's question.
Your entire response MUST be a single JSON object with a top-level key named "plan".
The value of "plan" must be a JSON array of step objects.

**Rules for Steps:**
1.  **Logical Analysis:** The steps must logically lead to the user's answer. For data questions, this usually involves fetching, cleaning, analyzing (e.g., sorting, filtering), and then returning the result.
2.  **`run_python` Code:** The "code" argument for "run_python" steps MUST be a JSON array of strings, where each string is a single line of Python code.
3.  **`run_python` Output:** The script's result is what it prints to standard output. Therefore, the VERY LAST LINE of the "code" array MUST be a `print()` statement that outputs the final result.
4.  **`return` Step:** The final step must be of type "return". Its "from" argument must be a JSON array of previous step "id"s.

**Example Plan for Analyzing Data:**

{{
  "plan": [
    {{
      "id": "get_webpage",
      "type": "fetch_url",
      "args": {{"url": "https://example.com/data", "save_as": "page.html"}}
    }},
    {{
      "id": "get_table",
      "type": "extract_table",
      "args": {{"from": "get_webpage", "save_as": "data.csv"}}
    }},
    {{
      "id": "analyze_data",
      "type": "run_python",
      "args": {{
        "code": [
          "import pandas as pd",
          "df = pd.read_csv('data.csv')",
          "# Always clean data before analysis",
          "df['Revenue'] = df['Revenue'].replace('[\\$,]', '', regex=True).astype(float)",
          "# Always sort data to find top/bottom entries",
          "df_sorted = df.sort_values(by='Revenue', ascending=False)",
          "# Select the top 10 after sorting",
          "top_10 = df_sorted.head(10)",
          "print(top_10.to_json(orient='records'))"
        ]
      }}
    }},
    {{
      "id": "final_response",
      "type": "return",
      "args": {{"from": ["analyze_data"]}}
    }}
  ]
}}

These are the available files for you to use given by the user: \"\"\"{available_files}\"\"\"

Now, generate the complete JSON object response for the user's question:
\"\"\"{question_text}\"\"\"
"""

    plan_str = await call_llm(
        model=settings.DEFAULT_MODEL,
        prompt=prompt,
        max_tokens=3072
    )

    print(f"Raw string from LLM (JSON Mode):\n{plan_str}")

    try:
        data = json.loads(plan_str)
        plan = data["plan"]
        if not isinstance(plan, list): raise TypeError("'plan' key must be a list.")
        print(f"Plan parsed successfully with {len(plan)} steps.")
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        print(f"FATAL: LLM output could not be parsed or was invalid. Error: {e}")
        print(f"--- BROKEN OUTPUT ---\n{plan_str}\n--------------------")
        raise ValueError(f"LLM returned unusable JSON: {e}")

    for step in plan:
        if step.get("type") not in allowed_types:
            raise ValueError(f"Plan is invalid: unsupported step type '{step.get('type')}' found.")

    print(f"Final parsed plan:\n{json.dumps(plan, indent=2)}")
    return plan
