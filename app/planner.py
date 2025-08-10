# planner.py (Uses JSON Mode and handles edge cases correctly)

import json
from .config import settings
from .llm import call_llm

async def plan_for_question(question_text: str, available_files: list[str]):
    """
    Generate an execution plan. Uses the LLM's JSON Mode and includes robust parsing
    to handle edge cases where the returned JSON may be incomplete or invalid.
    """
    print("Planning for question...")
    print(f"Question text: {question_text}")
    print(f"Available files: {available_files}")

    allowed_types = ["fetch_url", "read_file", "extract_table", "duckdb_query", "run_python", "plot", "summarize", "return"]

    # This prompt is now extremely specific about the required JSON structure.
    prompt = f"""
You are a planning agent for a data analysis pipeline.
Your entire response MUST be a single JSON object.
This object must have a single top-level key named "plan".
The value of "plan" must be a JSON array of step objects.
Each step object must have keys "id", "type", and "args".

**Rules for Steps:**
1.  **Data Flow:** The output of one step is used by another via the 'from' or 'df_ref' argument, which must point to a previous step's 'id'.
2.  **Allowed Step Types:** The "type" key must be one of: {json.dumps(allowed_types)}.
3.  **`run_python` Code:** For "run_python" steps, the "code" value is a JSON string. All backslashes (\\) and double quotes (") inside the Python code MUST be properly escaped. The script can read files saved by previous steps and its output is what it prints to standard output.
4.  **`return` Step:** The final step must be of type "return". Its "from" argument must be a JSON array of previous step "id"s to be assembled into the final response.

**Example Plan for a Multi-Part Question:**

{{
  "plan": [
    {{
      "id": "get_webpage",
      "type": "fetch_url",
      "args": {{"url": "https://example.com/data", "save_as": "page.html"}}
    }},
    {{
      "id": "get_table_from_page",
      "type": "extract_table",
      "args": {{"from": "get_webpage", "save_as": "data.csv"}}
    }},
    {{
      "id": "answer_question_1",
      "type": "run_python",
      "args": {{"code": "import pandas as pd; df = pd.read_csv('data.csv'); print(len(df[df['Year'] < 2000]))"}}
    }},
    {{
      "id": "answer_question_2",
      "type": "run_python",
      "args": {{"code": "import pandas as pd; df = pd.read_csv('data.csv'); print(df['Movie'].iloc[0])"}}
    }},
    {{
      "id": "create_plot",
      "type": "plot",
      "args": {{
          "df_ref": "get_table_from_page", 
          "x": "Rank", "y": "Peak", 
          "regression": true, "save_as": "plot.png"
      }}
    }},
    {{
      "id": "final_response",
      "type": "return",
      "args": {{"from": ["answer_question_1", "answer_question_2", "create_plot"]}}
    }}
  ]
}}

The user has provided the following files: {json.dumps(available_files)}.

Now, generate the complete JSON object response for the user's question:
\"\"\"{question_text}\"\"\"
"""

    plan_str = await call_llm(
        model=settings.DEFAULT_MODEL, # Using a capable model is important for following instructions
        prompt=prompt,
        max_tokens=3072 # Increased tokens to reduce chance of cutoff
    )

    print(f"Raw string from LLM (JSON Mode):\n{plan_str}")

    try:
        # We expect a JSON object with a 'plan' key.
        data = json.loads(plan_str)
        plan = data["plan"]

        if not isinstance(plan, list):
            raise TypeError("The 'plan' key does not contain a list.")

        print(f"Plan parsed successfully with {len(plan)} steps.")

    except json.JSONDecodeError as e:
        # This handles the primary edge case: the model's output was cut off and is not complete JSON.
        print(f"FATAL: LLM output was not complete JSON. Parser failed: {e}")
        print(f"--- BROKEN OUTPUT ---\n{plan_str}\n--------------------")
        raise ValueError(f"LLM returned incomplete JSON, preventing execution: {e}")

    except (KeyError, TypeError) as e:
        # This handles the case where the JSON is valid, but doesn't match our expected structure.
        print(f"FATAL: LLM JSON was valid, but didn't match the expected structure (e.g., missing 'plan' key). Error: {e}")
        print(f"--- INVALID STRUCTURE ---\n{plan_str}\n--------------------")
        raise ValueError(f"LLM returned JSON with an unexpected structure: {e}")

    # Final validation of step types
    for step in plan:
        stype = step.get("type")
        if stype not in allowed_types:
            raise ValueError(f"Plan is invalid: unsupported step type '{stype}' found.")

    print(f"Final parsed plan:\n{json.dumps(plan, indent=2)}")
    return plan
