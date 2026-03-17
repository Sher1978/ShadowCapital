import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
import os
from aiohttp import web
from config import BOT_TOKEN
from bot.handlers.client import client_router
from bot.handlers.admin import admin_router
from bot.handlers.settings import settings_router
from database.connection import init_db
from utils.scheduler import setup_scheduler

async def handle_health(request):
    return web.Response(text="Bot is alive")

async def start_health_server():
    app = web.Application()
    app.router.add_get("/", handle_health)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", "8080"))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.info(f"Health check server started on port {port}")

async def main() -> None:
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    
    # Start health check server for Cloud Run as early as possible
    await start_health_server()
    
    # Initialize DB
    await init_db()
    dp = Dispatcher()
    dp.include_router(admin_router)
    dp.include_router(settings_router)
    dp.include_router(client_router)
    
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    
    # Setup Scheduler
    from utils.scheduler import setup_scheduler, reload_admin_jobs
    scheduler = setup_scheduler(bot)
    scheduler.start()
    await reload_admin_jobs(bot)
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped")
