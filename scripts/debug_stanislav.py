import asyncio
import os
from datetime import datetime, timezone
from dotenv import load_dotenv
import sys
sys.path.append('.')
load_dotenv()
from database.firebase_db import FirestoreDB
from utils.gsheets_api import get_task_2_0, get_daily_task_from_sheets

async def debug_user(tg_id):
    print(f"--- Debugging TG ID: {tg_id} ---")
    
    # Try both DBs
    for db_id in ["(default)", "test-db-123456789"]:
        print(f"Checking DB: {db_id}")
        os.environ["FIREBASE_DATABASE_ID"] = db_id
        from firebase_admin import firestore
        try:
            db = firestore.client(database_id=db_id)
            doc = db.collection("users").where("tg_id", "==", tg_id).limit(1).stream()
            user_data = None
            for d in doc:
                user_data = d.to_dict()
                user_data['id'] = d.id
                break
            
            if user_data:
                print(f"FOUND USER in {db_id}:")
                print(f"Name: {user_data.get('full_name')}")
                print(f"Status: {user_data.get('status')}")
                print(f"Scenario: {user_data.get('scenario_type')}")
                start_date = user_data.get('sprint_start_date') or user_data.get('created_at')
                print(f"Start Date: {start_date}")
                
                if start_date:
                    if isinstance(start_date, str):
                        start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                    
                    now = datetime.now(timezone.utc)
                    day = (now - start_date).days + 1
                    print(f"Calculated Day: {day}")
                    
                    try:
                        task = await get_task_2_0(day, user_data.get('scenario_type') or "Sovereign")
                        if task:
                            print(f"Task 2.0 found for Day {day}: {task.get('day_name')}")
                            print(f"Levels available: {all(task.get(k) for k in ['task_light', 'task_medium', 'task_hard'])}")
                        else:
                            print(f"Task 2.0 NOT found for Day {day}. Trying fallback...")
                            fallback = await get_daily_task_from_sheets(day, user_data.get('scenario_type') or "Sovereign")
                            if fallback:
                                print(f"Fallback task found: {fallback[:50]}...")
                            else:
                                print(f"❌ NO TASK FOUND FOR DAY {day}")
                    except Exception as e:
                        print(f"❌ Error fetching task: {e}")
                
                print(f"Last Morning Sent: {user_data.get('last_morning_sent')}")
                return user_data
        except Exception as e:
            print(f"Error accessing DB {db_id}: {e}")
    return None

if __name__ == "__main__":
    # From previous dump: Stanislaav TG ID is 138999208
    asyncio.run(debug_user(138999208))
