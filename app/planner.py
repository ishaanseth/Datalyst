import os
import requests

from app import config

def plan_for_question(question: str):
    """Call AIPipe API to get a plan for the question."""
    token = config.AIPIPE_TOKEN
    if not token:
        raise ValueError("AIPIPE_TOKEN environment variable not set.")

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {
        "model": config.DEFAULT_MODEL,
        "messages": [{"role": "user", "content": f"Create a step-by-step data analysis plan for: {question}"}]
    }
    resp = requests.post(f"{config.AIPIPE_API_BASE}/chat/completions", headers=headers, json=payload)
    resp.raise_for_status()
    data = resp.json()
    return data
