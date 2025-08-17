# planner.py (Final Definitive Version)

import json
from .config import settings
from .llm import call_llm

async def plan_for_question(question_text: str, available_files: list[str]):
    print("Planning for question...")
    
    allowed_types = ["run_python", "return"]

    # This is the final, master prompt. It is simpler and more direct.
    prompt = f"""
You are a senior data analyst agent. Your job is to create a plan to answer the user's question by writing a single Python script.

**User's Question:**
\"\"\"{question_text}\"\"\"

**Available Files:**
{json.dumps(available_files)}

**Your Task:**
Create a JSON object with a key "plan". The plan must contain a single `run_python` step that does all the work.

**CRITICAL INSTRUCTIONS for the `run_python` script:**
1.  Read the necessary files from the `Available Files` list (e.g., `pd.read_csv('edges.csv')`).
2.  Import all required libraries (`pandas`, `networkx`, `matplotlib`, `base64`, `io`, `json`).
3.  Perform all calculations and generate all plots as requested.
4.  Store all final answers (both numbers and base64-encoded image URIs) in a single Python dictionary.
5.  **The VERY LAST LINE of your script MUST be `print(json.dumps(final_results_dict))`**. This is the only way to return the answer.

**EXAMPLE of a perfect `run_python` step:**
{{
  "id": "analyze_and_visualize",
  "type": "run_python",
  "args": {{
    "code": [
      "import pandas as pd",
      "import json",
      "final_results = {{}}",
      "df = pd.read_csv('sample-sales.csv')",
      "final_results['total_sales'] = df['sales'].sum()",
      "final_results['top_region'] = df.groupby('region')['sales'].sum().idxmax()",
      "print(json.dumps(final_results))"
    ]
  }}
}}

Now, generate the complete JSON plan with a single `run_python` step to solve the user's question.
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
