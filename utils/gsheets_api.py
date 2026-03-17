import gspread
from oauth2client.service_account import ServiceAccountCredentials
import logging
import os
import asyncio
from datetime import datetime
from config import GOOGLE_SHEET_URL as SPREADSHEET_URL

# Scope for Google Sheets and Drive
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

def get_gsheets_client():
    """
    Returns a gspread client using credentials.json.
    """
    creds_path = "credentials.json"
    if not os.path.exists(creds_path):
        logging.error("credentials.json not found. Google Sheets integration disabled.")
        return None
    
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, SCOPE)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        logging.error(f"Failed to authorize Google Sheets: {e}")
        return None


async def sync_user_to_sheets(user_data: dict):
    """
    Adds or updates a user in the USER_STATE sheet.
    """
    def _sync():
        client = get_gsheets_client()
        if not client: return
        
        try:
            sh = client.open_by_url(SPREADSHEET_URL)
            try:
                worksheet = sh.worksheet("USER_STATE")
            except gspread.WorksheetNotFound:
                worksheet = sh.add_worksheet(title="USER_STATE", rows="100", cols="10")
                worksheet.append_row([
                    "User_ID", "Имя", "Quality_L1", "Scenario", 
                    "SFI_Index", "Red_Flags", "Friction_Level", 
                    "Last_Insight", "Last_Update"
                ])
            
            sfi = user_data.get('sfi_index', 1.0)
            flags = user_data.get('red_flags', 0)
            friction = "🟢 GREEN"
            if sfi > 0.7 or flags >= 3:
                friction = "🔴 RED"
            elif sfi > 0.4 or flags >= 2:
                friction = "🟡 YELLOW"

            cell = worksheet.find(str(user_data['user_id']))
            row_data = [
                str(user_data['user_id']),
                user_data.get('name', ''),
                user_data.get('target_quality', ''),
                user_data.get('scenario', ''),
                str(round(sfi, 2)),
                str(flags),
                friction,
                user_data.get('last_insight', ''),
                datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            ]
            
            if cell:
                worksheet.update(f"A{cell.row}:I{cell.row}", [row_data])
            else:
                worksheet.append_row(row_data)
        except Exception as e:
            logging.error(f"Error syncing user to sheets: {e}")

    await asyncio.to_thread(_sync)

async def get_daily_task_from_sheets(day: int, scenario: str):
    """
    Fetches task from CONTENT_TIMELINE sheet based on day and scenario.
    """
    def _get_task():
        client = get_gsheets_client()
        if not client: return None
        try:
            sh = client.open_by_url(SPREADSHEET_URL)
            worksheet = sh.worksheet("CONTENT_TIMELINE")
            records = worksheet.get_all_records()
            for row in records:
                if str(row.get('День')) == str(day) and row.get('Этап', '').lower() == scenario.lower():
                    return row.get('Задание (Task_Body)')
            for row in records:
                if str(row.get('День')) == str(day):
                    return row.get('Задание (Task_Body)')
        except Exception as e:
            logging.error(f"Error getting task from sheets: {e}")
        return None

    return await asyncio.to_thread(_get_task)

async def get_evening_question_from_sheets():
    """
    Fetches questions from EVENING_LOGS sheet.
    """
    def _get_questions():
        client = get_gsheets_client()
        if not client: return None
        try:
            sh = client.open_by_url(SPREADSHEET_URL)
            worksheet = sh.worksheet("EVENING_LOGS")
            records = worksheet.get_all_records()
            if records:
                return [r.get('Вопрос') for r in records if r.get('Вопрос')]
        except Exception as e:
            logging.error(f"Error getting evening questions: {e}")
        return None

    return await asyncio.to_thread(_get_questions)
