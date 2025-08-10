# llm.py

import httpx
import json
from .config import settings

def call_llm(model: str, prompt: str, max_tokens: int = 2048) -> str:
    """
    Makes a request to the AI Pipe / OpenRouter proxy to get a response from an LLM.
    """
    print("Calling LLM via AI Pipe proxy...")

    # Ensure the token is available from environment variables
    token = settings.AIPIPE_TOKEN
    if not token:
        print("ERROR: AIPIPE_TOKEN environment variable not set.")
        raise ValueError("AIPIPE_TOKEN is not configured. Please set it in your environment.")

    # API endpoint and headers
    api_base = settings.AIPIPE_API_BASE
    url = f"{api_base}/chat/completions"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # Request body in the format required by the Chat Completions API
    body = {
        "model": model,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "max_tokens": max_tokens,
        "temperature": 0.0, # Make it deterministic for planning
    }

    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(url, headers=headers, json=body)

        # Handle API errors
        if response.status_code != 200:
            print(f"ERROR: AI Pipe API returned status {response.status_code}")
            print(f"Response: {response.text}")
            response.raise_for_status() # Raise an exception for bad responses

        response_data = response.json()
        
        # Extract the content from the response
        content = response_data["choices"][0]["message"]["content"]
        print("LLM call successful, returning content.")
        return content.strip()

    except httpx.RequestError as e:
        print(f"ERROR: An HTTP error occurred while calling the LLM: {e}")
        raise
    except Exception as e:
        print(f"ERROR: An unexpected error occurred in call_llm: {e}")
        raise
