import gspread
from oauth2client.service_account import ServiceAccountCredentials
import logging
import os
import asyncio
import random
from datetime import datetime, timezone
from config import GOOGLE_SHEET_URL as SPREADSHEET_URL

# Scope for Google Sheets and Drive
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# --- Task Engine 2.0 Cache ---
_TASK_ENGINE_CACHE = {
    "data": None,
    "last_fetch": None
}
CACHE_TTL_SECONDS = 3600 # 1 hour

def get_gsheets_client():
    """
    Returns a fresh gspread client using credentials.
    Supports environment variable GOOGLE_CREDENTIALS (JSON string) or local file.
    """
    # 1. Try environment variable first (for Cloud Run)
    env_creds = os.getenv("GOOGLE_CREDENTIALS")
    if env_creds:
        try:
            import json
            import base64
            # Try to decode if it looks like base64
            try:
                decoded = base64.b64decode(env_creds).decode('utf-8')
                info = json.loads(decoded)
            except:
                # If not base64, try raw JSON
                info = json.loads(env_creds)
                
            creds = ServiceAccountCredentials.from_json_keyfile_dict(info, SCOPE)
            return gspread.authorize(creds)
        except Exception as e:
            logging.error(f"Failed to authorize Google Sheets via env var: {e}")

    # 2. Fallback to local files
    creds_paths = ["resources/google_credentials.json", "credentials.json"]
    creds_path = next((p for p in creds_paths if os.path.exists(p)), None)
    
    if not creds_path:
        logging.error("Google credentials not found (env GOOGLE_CREDENTIALS or local file).")
        return None
    
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, SCOPE)
        return gspread.authorize(creds)
    except Exception as e:
        logging.error(f"Failed to authorize Google Sheets via file {creds_path}: {e}")
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
                datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
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
    Fetches task from CONTENT_TIMELINE sheet based on day and scenario-specific column.
    """
    scenario_map = {
        "sovereign": "Sovereign (Власть и Границы)",
        "expansion": "Expansion (Наглость и Масштаб)",
        "vitality": "Vitality (Ресурс и Энергия)",
        "architect": "Architect (Интуиция и Хаос)"
    }
    
    # Normalize scenario name
    scenario_key = str(scenario).lower().strip()
    target_column = scenario_map.get(scenario_key, "Sovereign (Власть и Границы)")

    def _get_task():
        client = get_gsheets_client()
        if not client:
            logging.error("❌ Google Sheets client failed to initialize (check credentials.json)")
            raise RuntimeError("Google Sheets API client not initialized. Check credentials.")
            
        try:
            sh = client.open_by_url(SPREADSHEET_URL)
            worksheet = sh.worksheet("CONTENT_TIMELINE")
            records = worksheet.get_all_records()
            for row in records:
                if str(row.get('День')) == str(day):
                    task = row.get(target_column)
                    return task if task and str(task).strip() else None
        except Exception as e:
            err_msg = str(e)
            logging.error(f"❌ Error getting task from sheets: {err_msg}")
            # Identify specific API errors
            if "API has not been used" in err_msg or "disabled" in err_msg.lower():
                raise RuntimeError("Google Sheets API is DISABLED. Please enable it in Cloud Console.")
            if "permission" in err_msg.lower():
                raise RuntimeError("Permission denied for Spreadsheet. Check service account access (Editor).")
            if "not found" in err_msg.lower() and "worksheet" in err_msg.lower():
                raise RuntimeError("Worksheet 'CONTENT_TIMELINE' not found in the spreadsheet.")
            raise RuntimeError(f"GSheets error: {err_msg}")
    return await asyncio.to_thread(_get_task)

async def get_task_2_0(day: int, scenario: str):
    """
    Fetches multi-level task data from NEW_TASK_ENGINE sheet.
    Supports caching with TTL.
    """
    global _TASK_ENGINE_CACHE
    
    # 1. Check Cache
    now = datetime.now()
    if (_TASK_ENGINE_CACHE["data"] and _TASK_ENGINE_CACHE["last_fetch"] and 
        (now - _TASK_ENGINE_CACHE["last_fetch"]).total_seconds() < CACHE_TTL_SECONDS):
        records = _TASK_ENGINE_CACHE["data"]
    else:
        # 2. Fetch fresh data
        def _fetch_all():
            client = get_gsheets_client()
            if not client: return None
            try:
                sh = client.open_by_url(SPREADSHEET_URL)
                worksheet = sh.worksheet("NEW_TASK_ENGINE")
                # Using get_all_records maps headers to dict keys
                return worksheet.get_all_records()
            except Exception as e:
                logging.error(f"Error fetching NEW_TASK_ENGINE: {e}")
                return None
        
        records = await asyncio.to_thread(_fetch_all)
        if records:
            _TASK_ENGINE_CACHE["data"] = records
            _TASK_ENGINE_CACHE["last_fetch"] = now
            logging.info("🔄 Task Engine Cache Updated.")
        else:
            # If fetch fails, try using stale cache
            records = _TASK_ENGINE_CACHE["data"]

    if not records:
        return None

    # 3. Find specific row
    target_scenario = str(scenario).lower().strip()
    for row in records:
        # Normalize scenario from sheet
        sheet_scenario = str(row.get('Scenario', '')).lower().strip()
        sheet_day = str(row.get('Day', ''))
        
        if sheet_day == str(day) and (sheet_scenario == target_scenario or sheet_scenario == "all"):
            return {
                "day_name": row.get('Day Name', f"День {day}"),
                "theory": row.get('Theory', ''),
                "task_light": row.get('Task_LIGHT', ''),
                "task_medium": row.get('Task_MEDIUM', ''),
                "task_hard": row.get('Task_HARD', ''),
                "guard_trap": row.get('Guard_Trap', ''),
                "evening_report": row.get('Evening_Report', '')
            }
            
    return None

async def get_evening_question_from_sheets(user_day: int, scenario: str):
    """
    Fetches questions from EVENING_LOGS sheet based on user_day and scenario.
    Matches the actual column structure with specific question fields.
    """
    def _get_questions():
        client = get_gsheets_client()
        if not client:
            logging.error("❌ Google Sheets client failed to initialize (check credentials.json)")
            raise RuntimeError("Google Sheets API client not initialized. Check credentials.")
        
        # 1. Determine week
        if 1 <= user_day <= 7: week = 1
        elif 8 <= user_day <= 14: week = 2
        elif 15 <= user_day <= 21: week = 3
        elif 22 <= user_day <= 30: week = 4
        else: week = 1 # Fallback
        
        try:
            sh = client.open_by_url(SPREADSHEET_URL)
            worksheet = sh.worksheet("EVENING_LOGS")
            records = worksheet.get_all_records()
            
            # 2. Filter by week and scenario (Matching Сценарий (L2) column)
            target_scenario = str(scenario).lower().strip()
            matches = [
                r for r in records 
                if str(r.get('Неделя')) == str(week) and str(r.get('Сценарий (L2)', '')).lower().strip() == target_scenario
            ]
            
            # 3. Fallback to "Общий" if no scenario-specific questions found
            if not matches:
                matches = [
                    r for r in records 
                    if str(r.get('Неделя')) == str(week) and str(r.get('Сценарий (L2)', '')).lower().strip() in ["общий", "общее"]
                ]
            
            if not matches:
                return None
                
            # 4. Pick random variant
            selected_row = random.choice(matches)
            
            # 5. Concatenate questions based on actual column names
            questions = []
            question_cols = ["1 (Факт)", "2 (Трение)", "3 (Хранитель)", "4 (Инсайт)"]
            for col in question_cols:
                q = selected_row.get(f'Вопрос {col}')
                if q and str(q).strip():
                    questions.append(str(q).strip())
            
            return "\n\n".join(questions) if questions else None

        except Exception as e:
            err_msg = str(e)
            logging.error(f"❌ Error getting evening questions: {err_msg}")
            if "API has not been used" in err_msg or "disabled" in err_msg.lower():
                raise RuntimeError("Google Sheets API is DISABLED. Please enable it in Cloud Console.")
            if "permission" in err_msg.lower():
                raise RuntimeError("Permission denied for Spreadsheet. Check service account access (Editor).")
            if "not found" in err_msg.lower() and "worksheet" in err_msg.lower():
                raise RuntimeError("Worksheet 'EVENING_LOGS' not found in the spreadsheet.")
            raise RuntimeError(f"GSheets evening error: {err_msg}")
        return None

    return await asyncio.to_thread(_get_questions)

async def delete_user_from_sheets(user_id: int):
    """
    Removes a user row from the USER_STATE sheet by User_ID.
    """
    def _delete():
        client = get_gsheets_client()
        if not client:
            logging.error("❌ Google Sheets client failed to initialize")
            raise RuntimeError("Google Sheets client not initialized.")
        
        try:
            sh = client.open_by_url(SPREADSHEET_URL)
            worksheet = sh.worksheet("USER_STATE")
            cell = worksheet.find(str(user_id))
            if cell:
                worksheet.delete_rows(cell.row)
                logging.info(f"🗑 Deleted user {user_id} from Google Sheets.")
        except Exception as e:
            err_msg = str(e)
            logging.error(f"❌ Error deleting user from sheets: {err_msg}")
            if "API has not been used" in err_msg or "disabled" in err_msg.lower():
                raise RuntimeError("Google Sheets API is DISABLED. Action required.")
            raise RuntimeError(f"GSheets delete error: {err_msg}")

    await asyncio.to_thread(_delete)
async def sync_sfi_analytics(user_data: dict):
    """
    Syncs detailed SFI metrics to the SFI_Analytics sheet.
    Expected keys: user_id, name, date, level, status, discomfort, penalty, sfi_score, zone
    """
    def _sync():
        client = get_gsheets_client()
        if not client: return
        
        try:
            sh = client.open_by_url(SPREADSHEET_URL)
            try:
                worksheet = sh.worksheet("SFI_Analytics")
            except gspread.WorksheetNotFound:
                worksheet = sh.add_worksheet(title="SFI_Analytics", rows="1000", cols="10")
                worksheet.append_row([
                    "User_ID", "Имя", "Дата", "Level (1-3)", 
                    "Status (0-1)", "Discomfort (0-10)", "Penalty", 
                    "SFI_Score (%)", "Zone", "Timestamp"
                ])
            
            row_data = [
                str(user_data['user_id']),
                user_data.get('name', ''),
                user_data.get('date', datetime.now().strftime("%Y-%m-%d")),
                user_data.get('level', ''),
                user_data.get('status', ''),
                user_data.get('discomfort', ''),
                user_data.get('penalty', 0),
                f"{user_data.get('sfi_score', 0)}%",
                user_data.get('zone', ''),
                datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            ]
            worksheet.append_row(row_data)
        except Exception as e:
            logging.error(f"Error syncing SFI analytics: {e}")

    await asyncio.to_thread(_sync)
