import os

# AIPipe token (user must log in to retrieve it in web context)
AIPIPE_TOKEN = os.getenv("AIPIPE_TOKEN")

# API endpoint for AIPipe (proxy to OpenRouter)
AIPIPE_API_BASE = "https://aipipe.org/openrouter/v1"

# Default model
DEFAULT_MODEL = "openai/gpt-5-chat"

class Settings:
    def __init__(self):
        self.AIPIPE_TOKEN = os.getenv("AIPIPE_TOKEN")
        self.AIPIPE_API_BASE = "https://aipipe.org/openrouter/v1"
        self.DEFAULT_MODEL = "openai/gpt-5-chat"

        # Runtime settings
        self.WORK_DIR = os.getenv("WORK_DIR", "/tmp")
        self.MAX_JOB_SECONDS = int(os.getenv("MAX_JOB_SECONDS", "300"))

settings = Settings()
