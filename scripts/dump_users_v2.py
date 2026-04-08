import asyncio
import sys
import os
from dotenv import load_dotenv
sys.path.append('.')
load_dotenv() # Force load
from database.firebase_db import FirestoreDB
import logging

async def check():
    db_id = os.getenv("FIREBASE_DATABASE_ID")
    print(f"Using DB ID from env: {db_id}")
    
    docs = FirestoreDB.db.collection("users").stream()
    users = []
    for doc in docs:
        d = doc.to_dict()
        d['id'] = doc.id
        users.append(d)
    
    print(f"Total users in DB: {len(users)}")
    for u in users:
        print(f"Name: {u.get('full_name')}, ID: {u.get('id')}, TG: {u.get('tg_id')}, Status: {u.get('status')}")

if __name__ == "__main__":
    asyncio.run(check())
