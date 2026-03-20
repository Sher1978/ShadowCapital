import asyncio
import os
import logging
from dotenv import load_dotenv
from redis.asyncio import Redis
import firebase_admin
from firebase_admin import credentials
from google.cloud.firestore import AsyncClient

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestConnectivity")

async def test_redis():
    logger.info("📡 Testing Redis connection...")
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        logger.error("❌ REDIS_URL not found in .env")
        return False
    
    try:
        redis = Redis.from_url(redis_url)
        # Try a simple ping with a timeout
        await asyncio.wait_for(redis.ping(), timeout=5.0)
        logger.info("✅ Redis connection SUCCESSFUL!")
        await redis.aclose() # Updated to aclose()
        return True
    except asyncio.TimeoutError:
        logger.error("❌ Redis connection TIMEOUT (5s)")
    except Exception as e:
        logger.error(f"❌ Redis connection FAILED: {e}")
    return False

async def test_firestore():
    logger.info("🔥 Testing Async Firestore connection...")
    database_id = os.getenv("FIREBASE_DATABASE_ID", "(default)")
    
    try:
        if not firebase_admin._apps:
            cred_path = "credentials.json"
            if os.path.exists(cred_path):
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
            else:
                firebase_admin.initialize_app()
        
        db = AsyncClient(database=database_id)
        # Try a simple query
        logger.info(f"🔍 Querying collection 'users' in database '{database_id}'...")
        # doc().get() is async in AsyncClient
        docs = db.collection("users").limit(1).stream()
        count = 0
        async for _ in docs:
            count += 1
            break # Just need 1
            
        logger.info(f"✅ Firestore connection SUCCESSFUL! Found at least {count} users.")
        return True
    except Exception as e:
        logger.error(f"❌ Firestore connection FAILED: {e}")
    return False

async def main():
    r_ok = await test_redis()
    f_ok = await test_firestore()
    
    if r_ok and f_ok:
        logger.info("\n✨ ALL SYSTEMS GO!")
    else:
        logger.error("\n⚠️ SYSTEMS CHECK FAILED!")

if __name__ == "__main__":
    asyncio.run(main())
