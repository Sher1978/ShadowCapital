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
    # 1. Start health server IMMEDIATELY to satisfy Cloud Run
    await start_health_server()
    
    try:
        # 2. Lazy imports to pinpoint which module causes a hang/crash
        logger.info("📦 Importing aiogram...")
        from aiogram import Bot, Dispatcher
        from aiogram.enums import ParseMode
        from aiogram.client.default import DefaultBotProperties
        
        logger.info("📦 Importing config...")
        from config import BOT_TOKEN, ADMIN_IDS
        
        if not BOT_TOKEN:
            logger.error("❌ BOT_TOKEN is missing! Please set it in GitHub Secrets.")
            raise ValueError("BOT_TOKEN is None")

        logger.info("📦 Importing handlers...")
        from bot.handlers.client import client_router
        from bot.handlers.admin import admin_router
        from bot.handlers.settings import settings_router
        
        logger.info("📦 Importing database and scheduler...")
        from database.connection import init_db
        from utils.scheduler import setup_scheduler, reload_admin_jobs
        
        # 3. Initialize DB
        logger.info("🗄️ Initializing database...")
        await init_db()
        
        # 4. Initialize Bot
        logger.info("🤖 Connecting to Telegram...")
        bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        
        # Verify connection
        me = await bot.get_me()
        logger.info(f"✅ Connected as @{me.username} (ID: {me.id})")
        
        dp = Dispatcher()
        dp.include_router(admin_router)
        dp.include_router(settings_router)
        dp.include_router(client_router)
        
        # 5. Setup Scheduler
        logger.info("⏰ Starting scheduler...")
        scheduler = setup_scheduler(bot)
        scheduler.start()
        await reload_admin_jobs(bot)
        
        logger.info("🚀 Bot is ready and polling!")
        await dp.start_polling(bot)
        
    except Exception as e:
        logger.error(f"💥 CRITICAL STARTUP ERROR: {e}", exc_info=True)
        # Keep the process alive so the health server stays up and we can see the logs
        while True:
            await asyncio.sleep(3600)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("👋 Bot stopped by user")
