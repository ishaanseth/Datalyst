# llm.py (Corrected for async)

import httpx
import json
from .config import settings

# This function must be async to be awaited
async def call_llm(model: str, prompt: str, max_tokens: int = 2048) -> str:
    """
    Makes an asynchronous request to the AI Pipe / OpenRouter proxy to get a response from an LLM.
    """
    print("Calling LLM via AI Pipe proxy...")

    token = settings.AIPIPE_TOKEN
    if not token:
        print("ERROR: AIPIPE_TOKEN environment variable not set.")
        raise ValueError("AIPIPE_TOKEN is not configured. Please set it in your environment.")

    api_base = settings.AIPIPE_API_BASE
    url = f"{api_base}/chat/completions"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    body = {
        "model": model,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "max_tokens": max_tokens,
        "temperature": 0.0,
    }

    try:
        # Use httpx.AsyncClient for async requests
        async with httpx.AsyncClient(timeout=60.0) as client:
            # The client call itself must also be awaited
            response = await client.post(url, headers=headers, json=body)

        if response.status_code != 200:
            print(f"ERROR: AI Pipe API returned status {response.status_code}")
            print(f"Response: {response.text}")
            response.raise_for_status()

        response_data = response.json()
        content = response_data["choices"][0]["message"]["content"]
        print("LLM call successful, returning content.")
        return content.strip()

    except httpx.RequestError as e:
        print(f"ERROR: An HTTP error occurred while calling the LLM: {e}")
        raise
    except Exception as e:
        print(f"ERROR: An unexpected error occurred in call_llm: {e}")
        raise
