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

logger.info("🚩 [STARTUP] Polling Mode Initialized")

# --- Helper: Health Check Server ---
async def handle_health(request):
    return web.Response(text="Bot health check passed")

async def start_health_server():
    app = web.Application()
    app.router.add_get("/", handle_health)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", "8080"))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"🏥 Health server started on port {port}")

async def main() -> None:
    """
    Main entry point (Polling mode + Health Server).
    """
    # 1. Start Health Server (Required for Cloud Run)
    await start_health_server()
    
    try:
        # 2. Delayed (Lazy) Imports for Fast Startup
        logger.info("📦 [STARTUP] Phase 2.1: Loading config...")
        import config
        from config import BOT_TOKEN
        logger.info("📦 [STARTUP] Phase 2.2: Loading handlers...")
        from bot.handlers.client import client_router
        from bot.handlers.admin import admin_router
        from bot.handlers.settings import settings_router
        logger.info("📦 [STARTUP] Phase 2.3: Loading middlewares...")
        from bot.middlewares.fsm_reset import FsmResetMiddleware
        logger.info("📦 [STARTUP] Phase 2.4: Loading scheduler...")
        from utils.scheduler import setup_scheduler, reload_admin_jobs
        
        from aiogram import Bot, Dispatcher
        from aiogram.enums import ParseMode
        from aiogram.client.default import DefaultBotProperties
        
        if not BOT_TOKEN:
            raise ValueError("BOT_TOKEN is missing")

        bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        
        # Redis Setup
        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            from aiogram.fsm.storage.redis import RedisStorage
            from redis.asyncio import Redis
            storage = RedisStorage(Redis.from_url(redis_url))
        else:
            from aiogram.fsm.storage.memory import MemoryStorage
            storage = MemoryStorage()

        dp = Dispatcher(storage=storage)
        
        # Register Middlewares & Routers
        dp.message.outer_middleware(FsmResetMiddleware())
        dp.include_router(admin_router)
        dp.include_router(settings_router)
        dp.include_router(client_router)

        # 3. APScheduler
        scheduler = setup_scheduler(bot)
        scheduler.start()
        await reload_admin_jobs(bot)

        # 4. Start Polling
        logger.info("🚀 Bot starting (Polling mode)...")
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
        
    except Exception as e:
        logger.error(f"💥 FATAL ERROR: {e}", exc_info=True)
        # Sleep for an hour on fatal error to avoid crash looping on Cloud Run
        await asyncio.sleep(3600)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("👋 Bot stopped")
