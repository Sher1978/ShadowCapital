import asyncio
import os
from dotenv import load_dotenv
import sys
sys.path.append('.')
load_dotenv()
from database.firebase_db import FirestoreDB

async def check_logs(doc_id):
    print(f"--- Logs for {doc_id} ---")
    os.environ["FIREBASE_DATABASE_ID"] = "test-db-123456789"
    logs = await FirestoreDB.get_logs(doc_id, limit=5)
    for l in logs:
        print(f"{l.get('created_at')} | {l.get('type')}")

if __name__ == "__main__":
    asyncio.run(check_logs('mKhT0ByNL99om0naIS5n')) # Olga
