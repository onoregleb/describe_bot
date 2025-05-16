import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(override=True)

# Bot configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN is not set in environment variables")

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set in environment variables")

# OpenAI configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is not set in environment variables")

OPENAI_ORGANIZATION = os.getenv("OPENAI_ORGANIZATION")
if not OPENAI_ORGANIZATION:
    raise ValueError("OPENAI_ORGANIZATION is not set in environment variables")

# Yandex Search API
YANDEX_FOLDERID = os.getenv("YANDEX_FOLDERID")
if not YANDEX_FOLDERID:
    raise ValueError("YANDEX_FOLDERID is not set in environment variables")

YANDEX_API_KEY = os.getenv("YANDEX_API_KEY")
if not YANDEX_API_KEY:
    raise ValueError("YANDEX_API_KEY is not set in environment variables") 