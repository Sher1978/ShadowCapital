import gspread
from typing import List, Optional, Any, Dict
from oauth2client.service_account import ServiceAccountCredentials
import logging
import os
import asyncio
import random
from datetime import datetime, timezone
import time
from config import GOOGLE_SHEET_URL as SPREADSHEET_URL

# Scope for Google Sheets and Drive
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# --- Firebase-as-Cache Implementation ---
SHEET_NAME_TASK_ENGINE = "NEW_TASK_ENGINE"
SHEET_NAME_INSTRUCTIONS = "INSTRUCTIONS"

async def get_all_values(sheet_name: str) -> Optional[List[List[Any]]]:
    """Helper to fetch all values from a specific worksheet."""
    def _fetch():
        client = get_gsheets_client()
        if not client: return None
        try:
            sh = client.open_by_url(SPREADSHEET_URL)
            worksheet = sh.worksheet(sheet_name)
            return worksheet.get_all_values()
        except Exception as e:
            logging.error(f"Error fetching sheet {sheet_name}: {e}")
            return None
    return await asyncio.to_thread(_fetch)

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

async def sync_gsheets_to_firestore():
    """Fetch all data from GSheets and save to Firestore cache."""
    from database.firebase_db import FirestoreDB
    import logging
    
    logging.info("🔄 Starting GSheets to Firestore synchronization...")
    
    # 1. Sync Tasks Matrix
    all_values = await get_all_values(SHEET_NAME_TASK_ENGINE)
    if not all_values:
        raise RuntimeError("Could not fetch values from Task Engine sheet")
        
    COL_DAY = 0
    COL_SCENARIO = 1
    COL_DAY_NAME = 2
    COL_PHASE = 3
    COL_THEORY = 4
    COL_LIGHT = 5
    COL_MEDIUM = 6
    COL_HARD = 7
    COL_GUARD = 8
    COL_EVENING = 9
    
    tasks_to_cache = []
    # Skip header
    for row in all_values[1:]:
        if not row or len(row) <= COL_DAY: continue
        
        day_str = str(row[COL_DAY]).strip()
        if not day_str.isdigit(): continue
        
        tasks_to_cache.append({
            "day": int(day_str),
            "scenario": str(row[COL_SCENARIO] if len(row) > COL_SCENARIO else "").lower().strip() or "all",
            "day_name": row[COL_DAY_NAME] if len(row) > COL_DAY_NAME else f"День {day_str}",
            "phase": row[COL_PHASE] if len(row) > COL_PHASE else "",
            "theory": row[COL_THEORY] if len(row) > COL_THEORY else "",
            "task_light": row[COL_LIGHT] if len(row) > COL_LIGHT else "",
            "task_medium": row[COL_MEDIUM] if len(row) > COL_MEDIUM else "",
            "task_hard": row[COL_HARD] if len(row) > COL_HARD else "",
            "guard_trap": row[COL_GUARD] if len(row) > COL_GUARD else "",
            "evening_report": row[COL_EVENING] if len(row) > COL_EVENING else ""
        })
    
    if tasks_to_cache:
        await FirestoreDB.save_tasks_matrix(tasks_to_cache)
        logging.info(f"✅ Cached {len(tasks_to_cache)} tasks in Firestore.")
        
    # 2. Sync Instructions
    instruction_text = await fetch_instructions_from_sheets()
    if instruction_text:
        await FirestoreDB.save_global_content("instructions", instruction_text)
        logging.info("✅ Cached Instructions in Firestore.")
        
    return len(tasks_to_cache)

async def fetch_instructions_from_sheets():
    """Force fetch instructions from GSheets."""
    all_values = await get_all_values(SHEET_NAME_INSTRUCTIONS)
    if not all_values: return None
    
    text_parts = []
    # Skip header [Title, Content]
    for row in all_values[1:]:
        if len(row) >= 2:
            title = str(row[0]).strip()
            content = str(row[1]).strip()
            if title or content:
                text_parts.append(f"### {title}\n{content}")
    
    return "\n\n".join(text_parts)

async def get_instruction_text():
    """Get instruction text with Firestore cache as primary source."""
    from database.firebase_db import FirestoreDB
    from utils.texts import DEFAULT_INSTRUCTIONS
    
    # 1. Try cache
    try:
        cached = await FirestoreDB.get_cached_global_content("instructions")
        if cached:
            return cached
    except Exception as e:
        logging.warning(f"Instruction cache fetch failed: {e}")

    # 2. Fallback to GSheets
    text = await fetch_instructions_from_sheets()
    if text:
        return text
        
    return DEFAULT_INSTRUCTIONS

async def get_task_2_0(day: int, scenario: str) -> Optional[Dict[str, Any]]:
    """Fetch task with Firestore cache as primary source."""
    from database.firebase_db import FirestoreDB
    
    # 1. Try cache
    try:
        cached = await FirestoreDB.get_cached_task(day, scenario)
        if cached:
            return cached
    except Exception as e:
        logging.warning(f"Cache fetch failed: {e}")

    # 2. Fallback to GSheets (slow)
    logging.info(f"Cache miss for Day {day}, Scenario {scenario}. Falling back dummy to GSheets...")
    
    COL_DAY = 0
    COL_SCENARIO = 1
    COL_DAY_NAME = 2
    COL_PHASE = 3
    COL_THEORY = 4
    COL_LIGHT = 5
    COL_MEDIUM = 6
    COL_HARD = 7
    COL_GUARD = 8
    COL_EVENING = 9

    records = await get_all_values(SHEET_NAME_TASK_ENGINE)
    if not records: return None

    target_scenario = str(scenario).lower().strip()
    for row in records[1:]:
        if not row: continue
        sheet_scenario = str(row[COL_SCENARIO] if len(row) > COL_SCENARIO else "").lower().strip()
        sheet_day = str(row[COL_DAY] if len(row) > COL_DAY else "")
        
        if sheet_day == str(day) and (sheet_scenario == target_scenario or sheet_scenario in ["all", ""]):
            return {
                "day_name": row[COL_DAY_NAME] if len(row) > COL_DAY_NAME else f"День {day}",
                "phase": row[COL_PHASE] if len(row) > COL_PHASE else "",
                "theory": row[COL_THEORY] if len(row) > COL_THEORY else "",
                "task_light": row[COL_LIGHT] if len(row) > COL_LIGHT else "",
                "task_medium": row[COL_MEDIUM] if len(row) > COL_MEDIUM else "",
                "task_hard": row[COL_HARD] if len(row) > COL_HARD else "",
                "guard_trap": row[COL_GUARD] if len(row) > COL_GUARD else "",
                "evening_report": row[COL_EVENING] if len(row) > COL_EVENING else ""
            }
    return None

async def get_evening_question_from_sheets(day, scenario="Sovereign"):
    """
    Get evening questions. 
    Task Engine 2.0 now includes this in task_data.
    """
    task_data = await get_task_2_0(day, scenario)
    if task_data and task_data.get('evening_report'):
        return task_data['evening_report']
    
    return None

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
