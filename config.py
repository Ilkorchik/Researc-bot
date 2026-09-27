import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5")

SCOPUS_API_KEY = os.getenv("SCOPUS_API_KEY", "")
WOS_API_KEY = os.getenv("WOS_API_KEY", "")

MAX_RESULTS_PER_SOURCE = int(os.getenv("MAX_RESULTS_PER_SOURCE", "10"))
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "30"))
