import os
import json
import requests
from app import config

def plan_for_question(question: str, available_files: list[str]):
    """
    Call AIPipe API to generate a step-by-step data analysis plan.

    Args:
        question (str): The main question or analysis request text.
        available_files (list[str]): Filenames in the working directory that may be used.

    Returns:
        list[dict]: A list of steps, each step being a dictionary with at least:
            - "id": unique string identifier for the step
            - "type": type of step (e.g., "python", "query", "plot", "return")
            - "args": dict of arguments needed for that step

    Raises:
        ValueError: If AIPIPE_TOKEN is missing or the API response cannot be parsed into a valid plan.
    """
    token = config.AIPIPE_TOKEN
    if not token:
        raise ValueError("AIPIPE_TOKEN environment variable not set.")

    # Build prompt for LLM
    file_list_str = ", ".join(available_files) if available_files else "no extra files"
    user_prompt = (
        f"You are a data analysis planner. The user has asked:\n"
        f"{question}\n\n"
        f"The available data files are: {file_list_str}.\n"
        "Create a JSON list of analysis steps. Each step must be an object with:\n"
        "  - 'id': unique short name for the step (string)\n"
        "  - 'type': one of ['python', 'query', 'plot', 'return']\n"
        "  - 'args': a dictionary of arguments\n"
        "Ensure the final step has type 'return' and specifies the answer."
    )

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": config.DEFAULT_MODEL,
        "messages": [
            {"role": "system", "content": "You are a data analysis planning assistant."},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0
    }

    resp = requests.post(
        f"{config.AIPIPE_API_BASE}/chat/completions",
        headers=headers,
        json=payload
    )
    resp.raise_for_status()
    data = resp.json()

    # Extract the text from the LLM response
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as e:
        raise ValueError(f"Unexpected API response format: {data}") from e

    # Try to parse JSON from the content
    try:
        plan = json.loads(content)
    except json.JSONDecodeError:
        raise ValueError(f"Planner did not return valid JSON: {content}")

    # Validate the plan
    if not isinstance(plan, list) or not all(isinstance(step, dict) for step in plan):
        raise ValueError(f"Planner returned invalid plan format: {plan}")

    for step in plan:
        if not {"id", "type", "args"}.issubset(step.keys()):
            raise ValueError(f"Step missing required keys: {step}")

    return plan
