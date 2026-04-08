import asyncio
import os
from database.firebase_db import FirestoreDB

async def main():
    print("--- Searching for ANY user named Roman ---")
    docs = FirestoreDB.db.collection("users").stream()
    found = False
    for doc in docs:
        u = doc.to_dict()
        u['id'] = doc.id
        first_name = u.get('first_name', '')
        last_name = u.get('last_name', '')
        full_name = u.get('full_name', '')
        username = u.get('username', '')
        
        search_str = f"{first_name} {last_name} {full_name} {username}"
        if 'Роман' in search_str or 'Roman' in search_str:
            found = True
            print(f"Found: {full_name} (@{username}) - ID: {u.get('tg_id')}")
            print(f"  Status: {u.get('status')}")
            print(f"  Scenario: {u.get('scenario_type')}")
            print(f"  Current Day: {u.get('current_day', user.get('day', 'N/A'))}")
            print("-" * 20)

    if not found:
        print("No user named Roman found.")

if __name__ == "__main__":
    asyncio.run(main())
