# planner.py (Final Definitive Version)

import json
from .config import settings
from .llm import call_llm

async def plan_for_question(question_text: str, available_files: list[str]):
    print("Planning for question...")
    
    # Restore the simple, reliable tools to the agent's toolbox
    allowed_types = ["fetch_url", "extract_table", "run_python", "return"]

    # This is the master prompt that teaches the hybrid strategy.
    prompt = f"""
You are a senior data analyst agent. Your job is to create a plan to answer the user's question.
You must create a JSON object with a key "plan" containing a list of steps.

**STRATEGY:**
- If the question requires data from a URL, use `fetch_url` and `extract_table` to get the data into a CSV file first.
- If the question requires analyzing a file that is ALREADY provided, you can read it directly in your Python script.
- Use a single `run_python` step to perform all the final data analysis, calculations, and plotting.

**CRITICAL RULES:**
1.  **The user has provided the following files:** {json.dumps(available_files)}. Your Python code can access these files directly by name.
2.  The "code" argument for `run_python` steps MUST be a JSON array of strings.
3.  The Python script you write MUST import all necessary libraries.
4.  To create plots, generate them in-memory, save to a BytesIO buffer, encode to a base64 string, and add the resulting data URI string to the final dictionary.
5.  The VERY LAST LINE of your `run_python` script MUST be `print(json.dumps(final_results_dict))`.

**EXAMPLE 1: Web Scraping and Analysis**
{{
  "plan": [
    {{ "id": "get_webpage", "type": "fetch_url", "args": {{"url": "https://en.wikipedia.org/wiki/...", "save_as": "page.html"}} }},
    {{ "id": "get_table", "type": "extract_table", "args": {{"from": "get_webpage", "save_as": "data.csv"}} }},
    {{ "id": "analyze", "type": "run_python", "args": {{ "code": ["import pandas as pd", "import json", "df = pd.read_csv('data.csv')", "results = {{}}", "results['total_rows'] = len(df)", "print(json.dumps(results))"] }} }},
    {{ "id": "final_return", "type": "return", "args": {{"from": ["analyze"]}} }}
  ]
}}

**EXAMPLE 2: Analysis of a Provided File (`edges.csv`)**
{{
  "plan": [
    {{
      "id": "analyze_network",
      "type": "run_python",
      "args": {{
        "code": [
          "import pandas as pd",
          "import networkx as nx",
          "import json",
          "df = pd.read_csv('edges.csv')",
          "G = nx.from_pandas_edgelist(df, 'source', 'target')",
          "results = {{}}",
          "results['edge_count'] = G.number_of_edges()",
          "print(json.dumps(results))"
        ]
      }}
    }},
    {{ "id": "final_return", "type": "return", "args": {{"from": ["analyze_network"]}} }}
  ]
}}

Now, generate the complete JSON plan to answer the user's question:
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
