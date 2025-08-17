# planner.py (Final Definitive Version)

import json
from .config import settings
from .llm import call_llm

async def plan_for_question(question_text: str, available_files: list[str]):
    print("Planning for question...")
    
    # The agent now only has one tool: the power to write and run Python.
    allowed_types = ["run_python"]

    prompt = f"""
You are a senior data analyst agent. Your job is to answer the user's question by writing a single Python script.

**User's Question:**
\"\"\"{question_text}\"\"\"

**Available Files:**
{json.dumps(available_files)}

**Your Task:**
Create a JSON object with a key "plan". The plan must contain a SINGLE `run_python` step that does all the work.

**CRITICAL INSTRUCTIONS for the `run_python` script:**
1.  Read the necessary files from the `Available Files` list (e.g., `pd.read_csv('sample-sales.csv')`).
2.  Import all required libraries (`pandas`, `networkx`, `matplotlib`, `base64`, `io`, `json`).
3.  Perform ALL calculations and generate ALL plots as requested by the user.
4.  Store all final answers (numbers, strings, and base64 image URIs) in a single Python dictionary.
5.  **The VERY LAST LINE of your script MUST be `print(json.dumps(final_results_dict))`**. This is the only way to return the answer.

**Example Plan for a Generic Data Task:**
{{
  "plan": [
    {{
      "id": "analyze_data_and_create_output",
      "type": "run_python",
      "args": {{
        "code": [
          "import pandas as pd",
          "import json",
          "final_results = {{}}",
          "# Always read the specific file mentioned in the question",
          "df = pd.read_csv('data.csv')", 
          "# Perform some calculations",
          "final_results['total_rows'] = len(df)",
          "final_results['first_value'] = df.iloc[0, 0]",
          "# The last line MUST print the dictionary",
          "print(json.dumps(final_results))"
        ]
      }}
    }}
  ]
}}

Now, generate the complete JSON plan to solve the user's question.
"""

    plan_str = await call_llm(model=settings.DEFAULT_MODEL, prompt=prompt, max_tokens=4096)
    print(f"Raw string from LLM (JSON Mode):\n{plan_str}")

    try:
        data = json.loads(plan_str)
        plan = data["plan"]
        if not isinstance(plan, list): raise TypeError("'plan' key must be a list.")
        print(f"Plan parsed successfully with {len(plan)} steps.")
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        raise ValueError(f"LLM returned unusable JSON: {e}")

    for step in plan:
        if step.get("type") not in allowed_types:
            raise ValueError(f"Plan is invalid: unsupported step type '{step.get('type')}' found.")

    print(f"Final parsed plan:\n{json.dumps(plan, indent=2)}")
    return plan
