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

logger.info("🚩 [STARTUP] Webhook Mode Initialized")

# --- Helper: Health Check ---
async def handle_health(request):
    return web.Response(text="Bot health check passed")

async def main() -> None:
    """
    Main entry point (Webhooks + Health Server Unified).
    """
    app = web.Application()
    
    try:
        # 1. Delayed (Lazy) Imports
        logger.info("📦 [STARTUP] Phase 2: Loading Project Modules...")
        import config
        from config import BOT_TOKEN
        from bot.handlers.client import client_router
        from bot.middlewares.fsm_reset import FsmResetMiddleware
        from bot.handlers.admin import admin_router
        from bot.handlers.settings import settings_router
        from utils.scheduler import setup_scheduler, reload_admin_jobs
        
        from aiogram import Bot, Dispatcher
        from aiogram.enums import ParseMode
        from aiogram.client.default import DefaultBotProperties
        from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
        
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
        dp.message.outer_middleware(FsmResetMiddleware())
        dp.include_router(admin_router)
        dp.include_router(settings_router)
        dp.include_router(client_router)

        # 2. Webhook Config
        WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
        # Fallback to the known service URL if not in env
        BASE_URL = os.getenv("SERVICE_URL", "https://shadow-sprint-bot-1097154359322.us-central1.run.app")
        webhook_url = f"{BASE_URL}{WEBHOOK_PATH}"
        
        # 3. APScheduler
        scheduler = setup_scheduler(bot)
        scheduler.start()
        await reload_admin_jobs(bot)

        # 4. aiohttp routes
        app.router.add_get("/", handle_health)
        
        # Webhook Handler
        webhook_requests_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
        webhook_requests_handler.register(app, path=WEBHOOK_PATH)
        setup_application(app, dp, bot=bot)

        # Set Webhook
        logger.info(f"🔗 Setting webhook to: {webhook_url}")
        await bot.set_webhook(url=webhook_url, drop_pending_updates=True)
        
        port = int(os.environ.get("PORT", "8080"))
        logger.info(f"🚀 Bot starting on port {port} (Webhook mode)")
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", port)
        await site.start()
        
        # Keep alive for Cloud Run
        await asyncio.Event().wait()
        
    except Exception as e:
        logger.error(f"💥 FATAL ERROR: {e}", exc_info=True)
        await asyncio.sleep(3600)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("👋 Bot stopped")
