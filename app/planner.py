# planner.py (Final Production Version)

import json
from .config import settings
from .llm import call_llm

async def plan_for_question(question_text: str, available_files: list[str]):
    print("Planning for question...")
    print(f"Question text: {question_text}")
    print(f"Available files: {available_files}")

    # We are simplifying the allowed types. The agent's power comes from run_python.
    allowed_types = ["read_file", "run_python", "return"]

    # This is the final, production-grade prompt.
    prompt = f"""
You are a senior data analyst agent. Your task is to create a plan to answer the user's question using the provided files.
The final output MUST be a single JSON object as specified in the user's question.

**Your plan should have one single `run_python` step that performs all the necessary work and prints the final JSON object.**

**CRITICAL RULES:**
1.  Your entire response to this prompt MUST be a single JSON object with a top-level key named "plan".
2.  The "plan" MUST be an array of steps.
3.  The "code" argument for "run_python" steps MUST be a JSON array of strings, where each string is a single line of Python code.
4.  The script you write MUST import all necessary libraries (e.g., pandas, networkx, matplotlib, base64, io).
5.  To generate plots, create them in-memory using matplotlib, save to a BytesIO buffer, encode to a base64 string, and then add that string to the final results dictionary. DO NOT use the 'plot' tool.
6.  The VERY LAST LINE of your `run_python` script MUST be `print(json.dumps(final_results_dict))` to output the final answer.

**EXAMPLE PLAN FOR A COMPLEX TASK:**

{{
  "plan": [
    {{
      "id": "analyze_sales_data",
      "type": "run_python",
      "args": {{
        "code": [
          "# Import all necessary libraries",
          "import pandas as pd",
          "import matplotlib.pyplot as plt",
          "import base64",
          "from io import BytesIO",
          "import json",
          "",
          "# --- 1. Load and Prepare Data ---",
          "df = pd.read_csv('sample-sales.csv')",
          "df['date'] = pd.to_datetime(df['date'])",
          "final_results = {{}}",
          "",
          "# --- 2. Perform Calculations ---",
          "final_results['total_sales'] = df['sales'].sum()",
          "final_results['top_region'] = df.groupby('region')['sales'].sum().idxmax()",
          "",
          "# --- 3. Generate a Plot (Bar Chart) ---",
          "plt.figure()",
          "df.groupby('region')['sales'].sum().plot(kind='bar', color='blue')",
          "plt.title('Total Sales by Region')",
          "plt.ylabel('Total Sales')",
          "buf = BytesIO()",
          "plt.savefig(buf, format='png')",
          "buf.seek(0)",
          "img_base64 = base64.b64encode(buf.read()).decode('utf-8')",
          "final_results['bar_chart'] = f'data:image/png;base64,{{img_base64}}'",
          "plt.close()",
          "",
          "# --- 4. Generate another Plot (Line Chart) ---",
          "plt.figure()",
          "df.set_index('date')['sales'].cumsum().plot(kind='line', color='red')",
          "plt.title('Cumulative Sales Over Time')",
          "buf2 = BytesIO()",
          "plt.savefig(buf2, format='png')",
          "buf2.seek(0)",
          "img_base64_2 = base64.b64encode(buf2.read()).decode('utf-8')",
          "final_results['cumulative_sales_chart'] = f'data:image/png;base64,{{img_base64_2}}'",
          "plt.close()",
          "",
          "# --- 5. Print the Final Assembled JSON Object ---",
          "print(json.dumps(final_results))"
        ]
      }}
    }},
    {{
      "id": "final_response",
      "type": "return",
      "args": {{"from": ["analyze_sales_data"]}}
    }}
  ]
}}

The user has provided the following files: {json.dumps(available_files)}.
Now, generate the complete JSON plan to answer the user's question:
\"\"\"{question_text}\"\"\"
"""

    plan_str = await call_llm(
        model=settings.DEFAULT_MODEL,
        prompt=prompt,
        max_tokens=4096 # Increased token limit for complex scripts
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
            # We are removing the simple plot and summarize tools now
            if step.get("type") in ["plot", "summarize", "fetch_url", "extract_table", "duckdb_query"]:
                continue
            raise ValueError(f"Plan is invalid: unsupported step type '{step.get('type')}' found.")

    print(f"Final parsed plan:\n{json.dumps(plan, indent=2)}")
    return plan
