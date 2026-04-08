import asyncio
import os
from aiogram import Bot
from dotenv import load_dotenv
import sys
sys.path.append('.')
load_dotenv()
from database.firebase_db import FirestoreDB
from utils.scheduler import send_morning_impulse

async def trigger_danil():
    bot_token = os.getenv("BOT_TOKEN")
    bot = Bot(token=bot_token)
    
    os.environ["FIREBASE_DATABASE_ID"] = "test-db-123456789"
    user = await FirestoreDB.get_user(1819873644) # Daniil
    
    if not user:
        print("❌ User not found in test-db-123456789")
        return

    print(f"🚀 Manually triggering morning impulse for {user.get('full_name')} ({user.get('tg_id')})...")
    try:
        count = await send_morning_impulse(bot, user)
        print(f"✅ Success! Sent count: {count}")
    except Exception as e:
        print(f"❌ Failed to send: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(trigger_danil())
