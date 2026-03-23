import os
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load .env file if it exists (local development)
if os.path.exists(".env"):
    load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# List of Telegram IDs that have admin rights
ADMIN_IDS = [int(id.strip()) for id in os.getenv("ADMIN_IDS", "").split(",") if id.strip()]
# Permanent fallback for Ihor Sher (Project Owner)
if 5590852305 not in ADMIN_IDS:
    ADMIN_IDS.append(5590852305)

def is_admin(user_id: int) -> bool:
    res = user_id in ADMIN_IDS
    logger.debug(f"🛡 [AUTH] Admin check for {user_id}: {res}")
    return res

# Google Sheets URL for daily tasks
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1vGvlttP6SqfSdBSiD8Z4pn3iSfBSthtus5H54MDnsP8/edit?usp=sharing"

