# planner.py (Final Definitive Version)

import json
from .config import settings
from .llm import call_llm

async def plan_for_question(question_text: str, available_files: list[str]):
    print("Planning for question...")
    
    # The agent now only has one tool: the power to write and run Python.
    allowed_types = ["run_python"]

    available_files_json = json.dumps(available_files)
    
    prompt = f'''
You are a senior data analyst agent. Your job is to answer the user's question by writing a single Python script.

**User's Question:**
"""{question_text}"""

**Available Files:**
{available_files_json}

**Your Task:**
Create a JSON object with a key "plan". The plan must contain a SINGLE `run_python` step that does all the work.

**CRITICAL INSTRUCTIONS for the `run_python` script:**
1.  **Wrap ALL code in try-except-finally** to ensure errors are caught and reported cleanly. Always print JSON in the finally block.
2.  Read the necessary files from the `Available Files` list (e.g., `pd.read_csv('sample-sales.csv')`).
3.  Import all required libraries (`pandas`, `networkx`, `matplotlib`, `base64`, `io`, `json`, `requests`).
4.  Perform ALL calculations and generate ALL plots as requested by the user.
5.  Store all final answers (numbers, strings, and base64 image URIs) in a single Python dictionary.
6.  If your task involves scraping a website, always use browser-style headers with `requests`, for example:
    `headers = {{'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}}`
    and pass them via `requests.get(url, headers=headers, timeout=30)`. Use BeautifulSoup or pd.read_html to **PARSE the HTML and extract data from tables**—not lxml directly. Always extract structured data (lists, dicts) from the parsed HTML, never return raw HTML.
7.  **Type Casting:** All numeric results from pandas/numpy (like `sum()`, `median()`, `corr()`) MUST be converted to standard Python types before being added to the final dictionary. Use `int()` for integers and `float()` for decimals.
8.  **REQUIRED STRUCTURE:** Wrap your entire script logic in a try-except-finally block:
    ```python
    final_results_dict = {{}}
    try:
        # All your logic here
        final_results_dict['result'] = ...
    except Exception as e:
        final_results_dict['error'] = str(e)
    finally:
        print(json.dumps(final_results_dict))
    ```
    This ensures the script ALWAYS outputs valid JSON, even on failure.

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
          "try:",
          "    df = pd.read_csv('data.csv')",
          "    final_results['total_rows'] = int(len(df))",
          "    final_results['first_value'] = str(df.iloc[0, 0])",
          "except Exception as e:",
          "    final_results['error'] = str(e)",
          "finally:",
          "    print(json.dumps(final_results))"
        ]
      }}
    }}
  ]
}}

**SCRAPING EXAMPLE:** If the task involves scraping a table from a webpage:
{{
  "plan": [
    {{
      "id": "scrape_film_data",
      "type": "run_python",
      "args": {{
        "code": [
          "import requests",
          "from bs4 import BeautifulSoup",
          "import json",
          "final_results = {{}}",
          "try:",
          "    url = 'https://en.wikipedia.org/wiki/List_of_highest-grossing_films'",
          "    headers = {{'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}}",
          "    response = requests.get(url, headers=headers, timeout=30)",
          "    response.raise_for_status()",
          "    soup = BeautifulSoup(response.text, 'html.parser')",
          "    table = soup.find('table', {{'class': 'wikitable'}})  # Find Wikipedia table",
          "    if not table:",
          "        raise ValueError('Table not found')",
          "    rows = []",
          "    for tr in table.find_all('tr')[1:]:  # Skip header row",
          "        cells = tr.find_all(['td', 'th'])",
          "        if len(cells) >= 3:",
          "            title = cells[2].get_text(strip=True)",
          "            gross = cells[3].get_text(strip=True)",
          "            year = cells[4].get_text(strip=True)",
          "            rows.append({{'title': title, 'worldwide_gross': gross, 'year': year}})",
          "            if len(rows) >= 50:  # Limit to top 50 films",
          "                break",
          "    final_results['highest_grossing_films'] = rows",
          "except Exception as e:",
          "    final_results['error'] = str(e)",
          "finally:",
          "    print(json.dumps(final_results))"
        ]
      }}
    }}
  ]
}}

Now, generate the complete JSON plan to solve the user's question.
'''

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
