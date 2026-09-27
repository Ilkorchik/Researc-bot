import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")

SCOPUS_API_KEY = os.getenv("SCOPUS_API_KEY", "")
WOS_API_KEY = os.getenv("WOS_API_KEY", "")

MAX_RESULTS_PER_SOURCE = int(os.getenv("MAX_RESULTS_PER_SOURCE", "10"))
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "30"))
