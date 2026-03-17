import asyncio
import logging
import sys
import os
from aiohttp import web

# Configure logging at the very top
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

async def handle_health(request):
    return web.Response(text="Bot health check passed")

async def start_health_server():
    """Starts a minimal health server on the port provided by Cloud Run."""
    try:
        app = web.Application()
        app.router.add_get("/", handle_health)
        runner = web.AppRunner(app)
        await runner.setup()
        port = int(os.environ.get("PORT", "8080"))
        site = web.TCPSite(runner, "0.0.0.0", port)
        await site.start()
        logger.info(f"🚀 Health check server live on port {port}")
    except Exception as e:
        logger.error(f"❌ Failed to start health server: {e}")

async def main() -> None:
    """
    Main entry point for the bot (Attempt 18 - Final Launch).
    Designed to be robust and provide clear logs at every step.
    """
    # 1. Start health server IMMEDIATELY to satisfy Cloud Run's port check
    logger.info("📡 Starting health server on port 8080...")
    await start_health_server()
    
    # Tiny sleep to let the OS/Cloud Run settle
    await asyncio.sleep(1)
    
    try:
        # 2. Sequential loading with explicit logs to catch the exact line of hang
        logger.info("📦 Step 1: Importing aiogram basic components...")
        from aiogram import Bot, Dispatcher
        
        logger.info("📦 Step 2: Importing aiogram enums/clients...")
        from aiogram.enums import ParseMode
        from aiogram.client.default import DefaultBotProperties
        
        logger.info("📦 Step 3: Loading bot configuration...")
        import config
        from config import BOT_TOKEN
        
        if not BOT_TOKEN:
            logger.error("❌ CRITICAL: BOT_TOKEN is empty! Check GitHub Secrets.")
            raise ValueError("BOT_TOKEN is missing")

        logger.info("📦 Step 4: Loading internal modules (handlers, db, utils)...")
        from bot.handlers.client import client_router
        from bot.handlers.admin import admin_router
        from bot.handlers.settings import settings_router
        from database.connection import init_db
        from utils.scheduler import setup_scheduler, reload_admin_jobs
        
        # 3. Database Initialization
        logger.info("🗄️ Step 5: Initializing SQLite database...")
        await init_db()
        
        # 4. Bot Initialization
        logger.info("🤖 Step 6: Connecting to Telegram API...")
        bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        
        # Verify connection (this will fail if token is wrong)
        me = await bot.get_me()
        logger.info(f"✅ Step 7: Successfully connected as @{me.username} (ID: {me.id})")
        
        dp = Dispatcher()
        dp.include_router(admin_router)
        dp.include_router(settings_router)
        dp.include_router(client_router)
        
        # 5. Scheduler Initialization
        logger.info("⏰ Step 8: Starting APScheduler and reloading jobs...")
        scheduler = setup_scheduler(bot)
        scheduler.start()
        await reload_admin_jobs(bot)
        
        logger.info("🚀 Step 9: Bot is now active and polling for updates!")
        await dp.start_polling(bot)
        
    except Exception as e:
        logger.error(f"💥 FATAL STARTUP ERROR: {e}", exc_info=True)
        # We MUST keep the process alive so the health server doesn't stop.
        # This allows Cloud Run to stay UP while we read the error logs.
        logger.info("🛑 Entering idle state to preserve logs. Fix error and redeploy.")
        while True:
            await asyncio.sleep(3600)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("👋 Bot stopped by user")
