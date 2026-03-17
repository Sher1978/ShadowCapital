import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# List of Telegram IDs that have admin rights
ADMIN_IDS = [int(id.strip()) for id in os.getenv("ADMIN_IDS", "").split(",") if id.strip()]

# Google Sheets URL for daily tasks
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1vGvlttP6SqfSdBSiD8Z4pn3iSfBSthtus5H54MDnsP8/edit?usp=sharing"

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not found in .env")
