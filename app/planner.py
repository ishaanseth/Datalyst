# planner.py (Final Definitive Version)

import json
from .config import settings
from .llm import call_llm

async def plan_for_question(question_text: str, available_files: list[str]):
    print("Planning for question...")
    
    # We only need two powerful tools now.
    allowed_types = ["run_python", "return"]

    # This is the final, master prompt that teaches the agent how to think.
    prompt = f"""
You are a senior data analyst agent. Your job is to create a plan to answer the user's question.
You must create a JSON object with a key "plan" containing a list of steps.

**STRATEGY:**
Your primary tool is `run_python`. The user will provide files. Your plan should consist of a SINGLE `run_python` step that reads the provided files, performs all necessary analysis, generates all plots, assembles the results into a single dictionary, and prints that dictionary as a JSON string.

**CRITICAL RULES:**
1.  **The user has provided the following files:** {json.dumps(available_files)}. Your Python code can access these files directly by name (e.g., `pd.read_csv('edges.csv')`). Do NOT use `fetch_url` or `extract_table` for files that are already provided.
2.  The `run_python` "code" argument MUST be a list of strings.
3.  The Python script MUST import all necessary libraries (pandas, networkx, matplotlib, base64, io, json).
4.  To create plots, generate them in-memory, save to a BytesIO buffer, encode to a base64 string, and add the resulting data URI string to the final dictionary.
5.  The VERY LAST LINE of your `run_python` script MUST be `print(json.dumps(final_results_dict))`.

**EXAMPLE PLAN for the Network Analysis Task:**
{{
  "plan": [
    {{
      "id": "analyze_network_and_visualize",
      "type": "run_python",
      "args": {{
        "code": [
          "import pandas as pd",
          "import networkx as nx",
          "import json",
          "import matplotlib.pyplot as plt",
          "import base64",
          "from io import BytesIO",
          "",
          "df = pd.read_csv('edges.csv')",
          "G = nx.from_pandas_edgelist(df, 'source', 'target')",
          "final_results = {{}}",
          "",
          "# 1. Calculations",
          "final_results['edge_count'] = G.number_of_edges()",
          "degrees = dict(G.degree())",
          "final_results['highest_degree_node'] = max(degrees, key=degrees.get)",
          "node_count = G.number_of_nodes()",
          "final_results['average_degree'] = sum(degrees.values()) / node_count if node_count > 0 else 0",
          "final_results['density'] = nx.density(G)",
          "try:",
          "    final_results['shortest_path_alice_eve'] = nx.shortest_path_length(G, source='Alice', target='Eve')",
          "except nx.NetworkXNoPath:",
          "    final_results['shortest_path_alice_eve'] = None",
          "",
          "# 2. Network Graph PNG",
          "plt.figure(figsize=(8, 6))",
          "nx.draw(G, with_labels=True, node_color='lightblue', edge_color='gray')",
          "buf = BytesIO()",
          "plt.savefig(buf, format='png')",
          "plt.close()",
          "buf.seek(0)",
          "final_results['network_graph'] = f'data:image/png;base64,{{base64.b64encode(buf.read()).decode('utf-8')}}'",
          "",
          "# 3. Degree Histogram PNG",
          "plt.figure(figsize=(8, 6))",
          "plt.hist(list(degrees.values()), bins=range(1, len(degrees)+1), color='green')",
          "plt.title('Degree Distribution')",
          "plt.xlabel('Degree')",
          "plt.ylabel('Frequency')",
          "buf = BytesIO()",
          "plt.savefig(buf, format='png')",
          "plt.close()",
          "buf.seek(0)",
          "final_results['degree_histogram'] = f'data:image/png;base64,{{base64.b64encode(buf.read()).decode('utf-8')}}'",
          "",
          "# 4. Final Output",
          "print(json.dumps(final_results))"
        ]
      }}
    }},
    {{
      "id": "final_response",
      "type": "return",
      "args": {{"from": ["analyze_network_and_visualize"]}}
    }}
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
        if not isinstance(plan, list): raise TypeError("'plan' key is not a list.")
        print(f"Plan parsed successfully with {len(plan)} steps.")
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        raise ValueError(f"LLM returned unusable JSON: {e}")

    # Simplified validation since we mostly expect run_python
    for step in plan:
        if step.get("type") not in allowed_types:
            raise ValueError(f"Plan is invalid: unsupported step type '{step.get('type')}' found.")

    print(f"Final parsed plan:\n{json.dumps(plan, indent=2)}")
    return plan
