import os
import logging
from firebase_functions import https_fn
from firebase_admin import initialize_app, firestore
from datetime import datetime, timezone

# Initialize Firebase Admin
initialize_app()
_db = None

def get_db():
    global _db
    if _db is None:
        _db = firestore.client()
    return _db

# Configure logging
logging.basicConfig(level=logging.INFO)

# Load environment variables/config
# In Cloud Functions, you can use os.getenv if secrets are configured
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1vGvlttP6SqfSdBSiD8Z4pn3iSfBSthtus5H54MDnsP8/edit?usp=sharing"
ADMIN_IDS = [260669598, 5590852305] # Defaulting to known admins from config.py
BOT_TOKEN = os.getenv("BOT_TOKEN")
RESEND_API_KEY = os.getenv("RESEND_API_KEY")

@https_fn.on_call()
def calculate_sfi(req: https_fn.CallableRequest) -> dict:
    """
    Handles SFI calculation, AI insight generation, logging, and notifications.
    """
    try:
        data = req.data
        name = data.get('name', 'Anonymous')
        contact = data.get('contact', 'None')
        answers = data.get('answers', {})
        
        # 1. Calculation Logic
        zone_scores = {
            'Expansion': sum([answers.get(q, 0) for q in ['q7', 'q8', 'q9']]), # A
            'Sovereign': sum([answers.get(q, 0) for q in ['q4', 'q5', 'q6']]), # B
            'Vitality': sum([answers.get(q, 0) for q in ['q1', 'q2', 'q3']]),  # C
            'Architect': sum([answers.get(q, 0) for q in ['q10', 'q11', 'q12']]) # D
        }
        
        total_score = sum(zone_scores.values())
        max_possible = 120 
        sfi_index = round(total_score / max_possible, 2)
        sfi_percent = int(sfi_index * 100)
        
        highest_zone = max(zone_scores, key=zone_scores.get)
        archetype = highest_zone
        
        # 2. AI Insight Generation (Gemini) - Full 4-zone diagnostic
        insight = generate_ai_insight(name, sfi_index, archetype, zone_scores)
        
        # 3. Persistence (Firestore) - For Bot context
        db = get_db()
        lead_id = f"W-{int(datetime.now().timestamp())}"
        lead_ref = db.collection('sfi_leads').document(lead_id)
        lead_data = {
            'name': name,
            'contact': contact,
            'sfi_score': sfi_percent,
            'archetype': archetype,
            'zone_scores': zone_scores,
            'insight': insight,
            'timestamp': firestore.SERVER_TIMESTAMP,
            'source': 'web'
        }
        lead_ref.set(lead_data)
        
        # 4. CRM Logging (Google Sheets)
        log_to_sheets(name, contact, sfi_percent, archetype, insight)
        
        # 5. Telegram Notification
        notify_admin(name, contact, sfi_percent, archetype, insight, lead_id)
        
        # 6. Email Report (if contact is an email)
        if "@" in contact and "." in contact:
            send_sfi_email(contact, name, sfi_percent, archetype, insight)
        
        return {
            'status': 'success',
            'sfi_score': sfi_percent,
            'archetype': archetype,
            'insight': insight,
            'zone_scores': zone_scores,
            'uuid': lead_id
        }
        
    except Exception as e:
        logging.error(f"Error in calculate_sfi: {e}")
        return {'status': 'error', 'message': str(e)}

def generate_ai_insight(name, sfi, archetype, zone_scores):
    """Calls Gemini to generate a sharp, multi-scenario diagnostic."""
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-pro')
        
        system_prompt = (
            "You are Shadow System AI. Tone: Cold, technical, elite, uncompromising brilliance. "
            "Your output must be structured as a 'Dossier' with a section for each of the 4 Shadow Zones. "
            "Language: Russian. Max 1000 characters. Structured with headers."
        )
        
        prompt = f"""
        User: {name}
        Total SFI: {sfi*100}%
        Prime Archetype: {archetype}
        
        Zones (Scores 0-30):
        - Vitality (Base Energy): {zone_scores['Vitality']}
        - Sovereign (Inner Power): {zone_scores['Sovereign']}
        - Expansion (Growth/Risk): {zone_scores['Expansion']}
        - Architect (Structure/Strategy): {zone_scores['Architect']}
        
        Task: 
        1. Give a summary of the 'Friction Tax' for each individual zone based on the score.
        2. Final Verdict: Why is this user's SFI at {sfi*100}%? What is the hidden sabotage pattern?
        Output structured for glass-morphic scroll view.
        """
        
        response = model.generate_content(f"{system_prompt}\n\n{prompt}")
        return response.text if response.text else "Система анализирует данные. Уровень трения зашкаливает."
    except Exception as e:
        logging.error(f"Gemini error: {e}")
        return "Диагностика во всех зонах подтверждает наличие Теневого Капитала. Требуется личный аудит."

def log_to_sheets(name, contact, sfi, archetype, insight):
    """Logs test results to Google Sheets."""
    try:
        import gspread
        import json
        from oauth2client.service_account import ServiceAccountCredentials
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds_json = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")
        if creds_json:
            creds_dict = json.loads(creds_json)
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        else:
            creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
            
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_url(GOOGLE_SHEET_URL)
        
        try:
            worksheet = spreadsheet.worksheet("SFI_test_results")
        except:
            worksheet = spreadsheet.add_worksheet(title="SFI_test_results", rows="100", cols="20")
            header = ["Timestamp", "UUID", "Name", "Contact", "SFI_Score", "Archetype", "Key_Pain", "AI_Insight", "Source"]
            worksheet.append_row(header)
            
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        uuid = f"W-{int(datetime.now().timestamp())}"
        row = [timestamp, uuid, name, contact, f"{sfi}%", archetype, "Full Deep Dive", insight[:500], "Web"]
        worksheet.append_row(row)
        
    except Exception as e:
        logging.error(f"Sheets error: {e}")

def notify_admin(name, contact, sfi, archetype, insight, uuid):
    """Sends TG notification to Igor."""
    if not BOT_TOKEN:
        return
    import requests
    import json
    
    text = (
        f"🚨 {hbold('НОВЫЙ ЛИД: SFI TEST')}\n\n"
        f"👤 {hbold('Имя:')} {name}\n"
        f"📱 {hbold('Контакт:')} {contact}\n"
        f"📊 {hbold('SFI Index:')} {sfi}%\n"
        f"👑 {hbold('Архетип:')} {archetype}\n\n"
        f"🔗 {hbold('Код доступа:')} {uuid}\n\n"
        f"👁 {hbold('AI Diagnostic:')}\n{insight[:300]}..."
    )
    
    # Simple HTML tags helper for requests
    def hbold(t): return f"<b>{t}</b>"
    
    text = (
        f"🚨 <b>НОВЫЙ ЛИД: SFI TEST</b>\n\n"
        f"👤 <b>Имя:</b> {name}\n"
        f"📱 <b>Контакт:</b> {contact}\n"
        f"📊 <b>SFI Index:</b> {sfi}%\n"
        f"👑 <b>Архетип:</b> {archetype}\n\n"
        f"🔗 <b>Код доступа:</b> {uuid}\n\n"
        f"👁 <b>AI Diagnostic:</b>\n{insight[:400]}..."
    )
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    keyboard = {
        "inline_keyboard": [[
            {"text": "📨 Написать", "url": f"https://t.me/{contact.replace('@', '')}" if '@' in contact else f"mailto:{contact}"},
            {"text": "📊 Посмотреть lead", "url": f"https://t.me/Shadowass1st_bot?start={uuid}"}
        ]]
    }
    
    for admin_id in ADMIN_IDS:
        payload = {
            "chat_id": admin_id,
            "text": text,
            "parse_mode": "HTML",
            "reply_markup": json.dumps(keyboard)
        }
        requests.post(url, json=payload)

def send_sfi_email(to_email, name, sfi_score, archetype, diagnostic_text):
    """Sends an SFI report via Resend API."""
    if not RESEND_API_KEY:
        logging.warning("📩 [EMAIL] Sending skipped: RESEND_API_KEY not set.")
        return False

    url = "https://api.resend.com/emails"
    headers = {
        "Authorization": f"Bearer {RESEND_API_KEY}",
        "Content-Type": "application/json"
    }

    # Format the HTML content
    diagnostic_html = diagnostic_text.replace('\n', '<br>')
    html_content = f"""
    <div style="font-family: sans-serif; max-width: 600px; margin: auto; padding: 20px; background-color: #0f172a; color: #f8fafc; border-radius: 12px; border: 1px solid #1e293b;">
        <h1 style="color: #38bdf8; text-align: center;">🗝 Shadow SFI: Ваш Досье</h1>
        <p>Привет, {name}!</p>
        <p>Ваш результат сканирования в системе SFI готов. Ниже представлены ключевые показатели Вашего Теневого Капитала.</p>
        
        <div style="background-color: #1e293b; padding: 15px; border-radius: 8px; margin: 20px 0;">
            <p style="margin: 0; font-size: 1.2em;">📊 <b>Итоговый SFI Index:</b> {sfi_score}%</p>
            <p style="margin: 0; font-size: 1.2em;">🏆 <b>Ведущий Архетип:</b> {archetype}</p>
        </div>

        <h3 style="color: #38bdf8; border-bottom: 1px solid #334155; padding-bottom: 5px;">🧬 ПОЛНАЯ ДИАГНОСТИКА:</h3>
        <div style="white-space: pre-wrap; line-height: 1.6; color: #cbd5e1;">
            {diagnostic_html}
        </div>

        <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #334155; text-align: center; color: #94a3b8; font-size: 0.9em;">
            <p>Это первый шаг к конвертации Теневого Капитала в реальный результат.</p>
            <p>Ожидайте сообщения от Игоря, мы уже анализируем Вашу стратегию.</p>
        </div>
    </div>
    """

    payload = {
        "from": "Shadow Sprint <onboarding@resend.dev>",
        "to": [to_email],
        "subject": f"🎯 Ваш SFI Отчет: {sfi_score}% — {archetype}",
        "html": html_content
    }

    try:
        import requests
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        logging.info(f"✅ [EMAIL] Report sent to {to_email}")
        return True
    except Exception as e:
        logging.error(f"❌ [EMAIL] Error sending to {to_email}: {e}")
        return False
