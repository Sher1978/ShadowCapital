import asyncio
import os
import sys
from database.firebase_db import FirestoreDB

# Set console to UTF-8
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

async def main():
    print("--- Searching for Roman Frolov (Comprehensive) ---")
    docs = FirestoreDB.db.collection("users").stream()
    found = False
    for doc in docs:
        u = doc.to_dict()
        u['id'] = doc.id
        full_name = str(u.get('full_name', '')).lower()
        username = str(u.get('username', '')).lower()
        first_name = str(u.get('first_name', '')).lower()
        
        if 'roman' in full_name or 'frolov' in full_name or 'roman' in username or 'frolov' in username or 'roman' in first_name:
            found = True
            print(f"Match: {u.get('full_name')} (@{u.get('username')})")
            print(f"  ID: {u.get('tg_id')}")
            print(f"  Status: {u.get('status')}")
            print(f"  Scenario: {u.get('scenario_type')}")
            print(f"  Current Level: {u.get('current_day_level')}")
            print("-" * 20)
            
    if not found:
        print("No matches found for Roman or Frolov.")

if __name__ == "__main__":
    asyncio.run(main())
