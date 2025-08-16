# planner.py (Definitive Hybrid Toolbox Version)

import json
from .config import settings
from .llm import call_llm

async def plan_for_question(question_text: str, available_files: list[str]):
    print("Planning for question...")
    
    allowed_types = ["fetch_url", "extract_table", "run_python", "return"]

    prompt = f"""
You are a senior data analyst agent. Your job is to create a plan to answer the user's question.
You must create a JSON object with a key "plan" containing a list of steps.

**STRATEGY:**
1.  Use the `fetch_url` and `extract_table` tools to get data from the web and into a CSV file. These tools are simple and reliable.
2.  Use a **single, final `run_python` step** to perform all the data analysis, calculations, and plotting.
3.  This final Python script will read the CSV from the previous step, do everything required, build a final Python dictionary for the results, and print it as a JSON string.

**RULES:**
1.  The `run_python` "code" argument MUST be a list of strings.
2.  The last line of the `run_python` script MUST be `print(json.dumps(final_results_dict))`.
3.  To create plots, import matplotlib, save the plot to an in-memory BytesIO buffer, and base64 encode it. Add the resulting data URI string to the final dictionary.

**EXAMPLE PLAN:**
{{
  "plan": [
    {{
      "id": "get_webpage",
      "type": "fetch_url",
      "args": {{"url": "https://en.wikipedia.org/wiki/List_of_highest-grossing_films", "save_as": "page.html"}}
    }},
    {{
      "id": "get_table_from_page",
      "type": "extract_table",
      "args": {{"from": "get_webpage", "save_as": "films.csv"}}
    }},
    {{
      "id": "analyze_and_prepare_results",
      "type": "run_python",
      "args": {{
        "code": [
          "import pandas as pd",
          "import json",
          "df = pd.read_csv('films.csv')",
          "final_results = {{}}",
          "# Calculate total sales",
          "df['SalesClean'] = df['Worldwide gross'].astype(str).replace('[\\\\$,]', '', regex=True).apply(pd.to_numeric, errors='coerce')",
          "final_results['total_sales'] = df['SalesClean'].sum()",
          "# Find top region",
          "final_results['top_region'] = df.groupby('Peak')['SalesClean'].sum().idxmax()",
          "# Add more calculations and plots here...",
          "print(json.dumps(final_results))"
        ]
      }}
    }},
    {{
      "id": "final_response",
      "type": "return",
      "args": {{"from": ["analyze_and_prepare_results"]}}
    }}
  ]
}}

The user has provided these files: {json.dumps(available_files)}.
Generate the complete JSON plan to answer the user's question:
\"\"\"{question_text}\"\"\"
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
