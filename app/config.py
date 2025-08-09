import os

# AIPipe token (user must log in to retrieve it in web context)
AIPIPE_TOKEN = os.getenv("AIPIPE_TOKEN")

# API endpoint for AIPipe (proxy to OpenRouter)
AIPIPE_API_BASE = "https://aipipe.org/openrouter/v1"

# Default model
DEFAULT_MODEL = "openai/gpt-4.1-nano"

class Settings:
    def __init__(self):
        self.aipipe_token = os.getenv("AIPIPE_TOKEN")
        self.aipipe_api_base = "https://aipipe.org/openrouter/v1"
        self.default_model = "openai/gpt-4.1-nano"

settings = Settings()
