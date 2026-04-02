import asyncio
from database.firebase_db import FirestoreDB
import logging

async def check():
    users = await FirestoreDB.get_active_users()
    print(f"Active users count: {len(users)}")
    for u in users:
        print(f"Name: {u.get('full_name')}, ID: {u.get('tg_id')}, Status: {u.get('status')}, TZ: {u.get('timezone')}, Evening: {u.get('evening_time')}, Last Evening: {u.get('last_evening_sent')}")

if __name__ == "__main__":
    asyncio.run(check())
