import asyncio
import sys
import os
sys.path.append('.')
from database.firebase_db import FirestoreDB
import logging

async def check():
    users = await FirestoreDB.get_active_users()
    print(f"Total active users: {len(users)}")
    for u in users:
        full_name = u.get('full_name', '')
        if 'данил' in full_name.lower() or 'danil' in full_name.lower() or 'daniil' in full_name.lower():
            print(f"--- FOUD DANIL ---")
            print(f"Name: {full_name}")
            print(f"ID (doc): {u.get('id')}")
            print(f"TG ID: {u.get('tg_id')}")
            print(f"Status: {u.get('status')}")
            print(f"Scenario: {u.get('scenario_type')}")
            print(f"Start Date: {u.get('sprint_start_date')}")
            print(f"Last Morning: {u.get('last_morning_sent')}")
            print(f"TZ: {u.get('timezone')}")
            print(f"Morning Time: {u.get('morning_time')}")
            print(f"Evening Time: {u.get('evening_time')}")

if __name__ == "__main__":
    asyncio.run(check())
