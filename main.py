import asyncio
import logging
import sys
import os
from aiohttp import web

# 0. Immediate Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

logger.info("🚩 [STARTUP] Phase 1: Environment Check")
logger.info(f"🐍 Python version: {sys.version}")
logger.info(f"📂 Working directory: {os.getcwd()}")
logger.info(f"💾 Service: {os.getenv('K_SERVICE', 'local')}")

logger.info("📦 [STARTUP] Phase 2: Loading Project Modules...")
import config
from config import BOT_TOKEN
from bot.handlers.client import client_router
from bot.middlewares.fsm_reset import FsmResetMiddleware
from bot.handlers.admin import admin_router
from bot.handlers.settings import settings_router
from database.connection import init_db
from utils.scheduler import setup_scheduler, reload_admin_jobs
logger.info("✅ Project modules loaded successfully")

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
logger.info("✅ aiogram loaded successfully")

# --- Helper: Health Check ---
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
    Main entry point for the bot (Attempt 36 - Admin Features & Stable GSheets).
    All heavy imports are now handled at the module level.
    """
    # 1. Start health server
    await start_health_server()
    
    try:
        if not BOT_TOKEN:
            logger.error("❌ CRITICAL: BOT_TOKEN is missing! Check GitHub Secrets.")
            raise ValueError("BOT_TOKEN is missing")

        # 2. Database Initialization
        logger.info("🗄️ Initializing SQLite database...")
        await init_db()
        
        # 3. Bot Initialization
        logger.info("🤖 Connecting to Telegram API...")
        bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        
        # Verify connection
        me = await bot.get_me()
        logger.info(f"✅ Successfully connected as @{me.username} (ID: {me.id})")
        
        dp = Dispatcher()
        dp.message.middleware(FsmResetMiddleware())
        dp.include_router(admin_router)
        dp.include_router(settings_router)
        dp.include_router(client_router)
        
        # 4. Scheduler Initialization
        logger.info("⏰ Starting APScheduler...")
        scheduler = setup_scheduler(bot)
        scheduler.start()
        await reload_admin_jobs(bot)
        
        logger.info("🚀 Bot is now active and polling!")
        await dp.start_polling(bot)
        
    except Exception as e:
        logger.error(f"💥 FATAL STARTUP ERROR: {e}", exc_info=True)
        # Keep process alive to preserve logs in Cloud Run
        while True:
            await asyncio.sleep(3600)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("👋 Bot stopped by user")
