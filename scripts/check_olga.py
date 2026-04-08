import asyncio
import os
from dotenv import load_dotenv
import sys
sys.path.append('.')
load_dotenv()
from database.firebase_db import FirestoreDB

async def check_user(doc_id):
    os.environ["FIREBASE_DATABASE_ID"] = "test-db-123456789"
    u = await FirestoreDB.get_user_by_doc_id(doc_id)
    if u:
        print(f"--- {u.get('full_name')} ({u.get('tg_id')}) ---")
        print(f"Status: {u.get('status')}")
        print(f"Last Morning: {u.get('last_morning_sent')}")
        print(f"TZ: {u.get('timezone')}")
        print(f"Morning Time: {u.get('morning_time')}")

async def run_all():
    # Olga's doc id is mKhT0ByNL99om0naIS5n
    await check_user('mKhT0ByNL99om0naIS5n')

if __name__ == "__main__":
    asyncio.run(run_all())
