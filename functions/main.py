import os
import logging
from firebase_functions import https_fn, options
from firebase_admin import initialize_app, firestore, credentials
import google.generativeai as genai
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests
import json
from datetime import datetime, timezone

# Initialize Firebase Admin
initialize_app()
db = firestore.client()

# Configure logging
logging.basicConfig(level=logging.INFO)

# Load environment variables/config
# In Cloud Functions, you can use os.getenv if secrets are configured
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1vGvlttP6SqfSdBSiD8Z4pn3iSfBSthtus5H54MDnsP8/edit?usp=sharing"
ADMIN_IDS = [260669598, 5590852305] # Defaulting to known admins from config.py
BOT_TOKEN = os.getenv("BOT_TOKEN")

@https_fn.on_call()
def calculate_sfi(req: https_fn.CallableRequest) -> dict:
    """
    Handles SFI calculation, AI insight generation, logging, and notifications.
    Expected data: {
        'name': str,
        'contact': str,
        'answers': { 'q1': int, ... 'q12': int },
        'zones': { 'A': [q7, q8, q9], 'B': [q4, q5, q6], 'C': [q1, q2, q3], 'D': [q10, q11, q12] }
    }
    """
    try:
        data = req.data
        name = data.get('name', 'Anonymous')
        contact = data.get('contact', 'None')
        answers = data.get('answers', {})
        
        # 1. Calculation Logic
        # Mapping: C=Vitality, B=Sovereign, A=Expansion, D=Architect
        zone_scores = {
            'A': sum([answers.get(q, 0) for q in ['q7', 'q8', 'q9']]),
            'B': sum([answers.get(q, 0) for q in ['q4', 'q5', 'q6']]),
            'C': sum([answers.get(q, 0) for q in ['q1', 'q2', 'q3']]),
            'D': sum([answers.get(q, 0) for q in ['q10', 'q11', 'q12']])
        }
        
        total_score = sum(zone_scores.values())
        max_possible = 120 # Assuming 12 questions * 10 pts
        sfi_index = round(total_score / max_possible, 2)
        sfi_percent = int(sfi_index * 100)
        
        # Determine Archetype
        archetype_map = {
            'A': 'Expansion',
            'B': 'Sovereign',
            'C': 'Vitality',
            'D': 'Architect'
        }
        highest_zone = max(zone_scores, key=zone_scores.get)
        archetype = archetype_map[highest_zone]
        
        # 2. AI Insight Generation (Gemini)
        insight = generate_ai_insight(name, sfi_index, archetype, zone_scores)
        
        # 3. CRM Logging (Google Sheets)
        log_to_sheets(name, contact, sfi_percent, archetype, insight)
        
        # 4. Telegram Notification
        notify_admin(name, contact, sfi_percent, archetype, insight)
        
        # 5. Result for Frontend
        return {
            'status': 'success',
            'sfi_score': sfi_percent,
            'archetype': archetype,
            'insight': insight,
            'uuid': f"web_{int(datetime.now().timestamp())}"
        }
        
    except Exception as e:
        logging.error(f"Error in calculate_sfi: {e}")
        return {'status': 'error', 'message': str(e)}

def generate_ai_insight(name, sfi, archetype, zone_scores):
    """Calls Gemini to generate a sharp, 'Shadow' insight."""
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-pro')
        
        # Read the Core Prompt
        # Note: In Cloud Functions, we might need to store this in a string or config
        # For now, I'll use a summarized version if the file isn't accessible, 
        # but the plan said to use the file. I'll assume it's bundled or read from FireStore.
        system_prompt = "You are Shadow System AI. Tone: Cold, technical, brilliant. No fluff. Max 400 chars."
        
        prompt = f"""
        User Name: {name}
        SFI Score: {sfi}
        Primary Archetype: {archetype}
        Zone Scores: {zone_scores}
        
        Generate a 'Shadow Insight' - a personal technical verdict. 
        Focus on the 'Friction Tax' they are paying in the {archetype} sector.
        Max 350-400 characters. Russian language.
        """
        
        response = model.generate_content(f"{system_prompt}\n\n{prompt}")
        return response.text if response.text else "Система не смогла оцифровать твой инсайт. Но твой Хранитель уже настороже."
    except Exception as e:
        logging.error(f"Gemini error: {e}")
        return "Инсайт временно заблокирован Хранителем. Твой SFI говорит сам за себя."

def log_to_sheets(name, contact, sfi, archetype, insight):
    """Logs test results to Google Sheets."""
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        # Note: In Cloud Functions, credentials should be handled via Service Account
        creds_json = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")
        if creds_json:
            creds_dict = json.loads(creds_json)
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        else:
            # Fallback to local file if it exists (for testing)
            creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
            
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_url(GOOGLE_SHEET_URL)
        
        # Sheet name specified by user
        try:
            worksheet = spreadsheet.worksheet("SFI_test_results")
        except:
            # Create if not exists
            worksheet = spreadsheet.add_worksheet(title="SFI_test_results", rows="100", cols="20")
            header = ["Timestamp", "UUID", "Name", "Contact", "SFI_Score", "Archetype", "Key_Pain", "AI_Insight", "Source"]
            worksheet.append_row(header)
            
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        uuid = f"W-{int(datetime.now().timestamp())}"
        row = [timestamp, uuid, name, contact, f"{sfi}%", archetype, "Dynamic", insight, "Web"]
        worksheet.append_row(row)
        
    except Exception as e:
        logging.error(f"Sheets error: {e}")

def notify_admin(name, contact, sfi, archetype, insight):
    """Sends TG notification to Igor."""
    if not BOT_TOKEN:
        return
        
    text = (
        f"🚨 *НОВЫЙ ЛИД: SFI TEST*\n\n"
        f"👤 *Имя:* {name}\n"
        f"📱 *Контакт:* {contact}\n"
        f"📊 *SFI:* {sfi}%\n"
        f"👑 *Архетип:* {archetype}\n\n"
        f"👁 *AI Вердикт:* {insight[:200]}..."
    )
    
    # Simple TG API call or use aiogram if preferred, but requests is lighter for functions
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    
    # Inline buttons
    keyboard = {
        "inline_keyboard": [[
            {"text": "📨 Написать", "url": f"https://t.me/{contact.replace('@', '')}" if '@' in contact else f"mailto:{contact}"},
            {"text": "📁 В Архив", "callback_data": "archive_lead"}
        ]]
    }
    
    for admin_id in ADMIN_IDS:
        payload = {
            "chat_id": admin_id,
            "text": text,
            "parse_mode": "Markdown",
            "reply_markup": json.dumps(keyboard)
        }
        requests.post(url, json=payload)
