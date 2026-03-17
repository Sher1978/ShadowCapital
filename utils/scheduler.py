from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from aiogram import Bot
from database.connection import get_db_session
from database.models import User, ShadowLog, GlobalSettings
from sqlalchemy import select, func
from sqlalchemy.orm import joinedload
from datetime import datetime, timedelta
import logging
from config import ADMIN_IDS
from utils.analysis import generate_weekly_briefing, generate_group_weekly_summary
from utils.gsheets_api import get_daily_task_from_sheets, get_evening_question_from_sheets
from aiogram.utils.markdown import hbold

_scheduler = None

async def send_admin_morning_pulse(bot: Bot):
    """09:00 UTC: Notify admin about SFI levels."""
    async with get_db_session() as session:
        stmt = select(User).where(User.status == "active")
        result = await session.execute(stmt)
        users = result.scalars().all()
        
        red_zone = [u for u in users if (u.sfi_index or 0) > 0.7 or (u.red_flags_count or 0) >= 3]
        
        text = (
            f"🌑 {hbold('Advisor, время сканирования.')}\n\n"
            f"Система обновила показатели SFI. В «красной зоне» сейчас {hbold(len(red_zone))} чел.\n"
            f"Проверь детали в разделе `🚀 Спринты`."
        )
        
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        builder = InlineKeyboardBuilder()
        builder.button(text="🚀 Спринты", callback_data="active_sprints_page_0")
        
        for admin_id in ADMIN_IDS:
            try: await bot.send_message(admin_id, text, reply_markup=builder.as_markup())
            except: pass

async def send_admin_deadline_control(bot: Bot):
    """20:30 UTC: List users who missed reports."""
    async with get_db_session() as session:
        # Simple check: active users who haven't sent a log today
        today = datetime.utcnow().date()
        stmt = select(User).where(User.status == "active").options(joinedload(User.logs))
        result = await session.execute(stmt)
        users = result.unique().scalars().all()
        
        missed = []
        for u in users:
            last_log = max([l.created_at for l in u.logs], default=None)
            if not last_log or last_log.date() < today:
                missed.append(f"• {u.full_name} (@{u.username or u.tg_id})")
        
        if not missed:
            text = "🚩 {hbold('Контроль дедлайна:')} Все отчеты сданы вовремя. Саботажа не обнаружено."
        else:
            text = (
                f"🚩 {hbold('Внимание: Сбор логов завершен.')}\n\n"
                f"Эти пользователи НЕ сдали отчет вовремя:\n"
                + "\n".join(missed) + "\n\n"
                f"Система готова к аудиту инсайтов."
            )
            
        for admin_id in ADMIN_IDS:
            try: await bot.send_message(admin_id, text)
            except: pass

async def send_admin_evening_concentrate(bot: Bot):
    """21:30 UTC: Summary of the day's insights."""
    async with get_db_session() as session:
        today = datetime.utcnow().date()
        # Fetch 5 latest insights from today's logs or user records
        stmt = select(User).where(User.status == "active", User.last_insight != None).order_by(User.sfi_index.desc()).limit(5)
        result = await session.execute(stmt)
        users = result.scalars().all()
        
        if not users: return

        insights = [f"• {hbold(u.full_name)}: {u.last_insight}" for u in users]
        
        text = (
            f"🧠 {hbold('Сводка инсайтов готова.')}\n\n"
            + "\n".join(insights) + "\n\n"
            f"Есть ли моменты для твоего личного вмешательства?"
        )
        
        for admin_id in ADMIN_IDS:
            try: await bot.send_message(admin_id, text)
            except: pass

async def send_morning_impulse(bot: Bot, user: User = None):
    """
    Sends morning impulse to a specific user or all active users.
    """
    now = datetime.utcnow()
    
    async with get_db_session() as session:
        if user:
            users = [user]
        else:
            stmt = select(User).where(User.role == "client").options(joinedload(User.shadow_map))
            result = await session.execute(stmt)
            users = result.unique().scalars().all()
            
        for u in users:
            if not u.shadow_map: continue
            
            # Calculate day
            start_date = u.sprint_start_date or u.created_at
            day = (now - start_date).days + 1
            
            # Fetch from Sheets
            task_body = await get_daily_task_from_sheets(day, u.scenario_type or "Sovereign")
            if not task_body:
                task_body = "Продолжай интеграцию твоего качества. Хранитель сегодня спокоен."
            
            text = (
                f"☀️ {u.shadow_map.quality_name}: Утренний Импульс (День {day})\n\n"
                f"{task_body}\n\n"
                f"Помни про обход Хранителя — действуй мягко."
            )
            
            try:
                await bot.send_message(u.tg_id, text)
                # If it's a specific user trigger, we don't necessarily want to mark it as 'sent today' 
                # to prevent blocking the actual scheduled message, but for simplicity we can.
                u.last_morning_sent = now
                logging.info(f"Morning impulse sent to {u.tg_id}")
            except Exception as e:
                logging.error(f"Failed to send morning to {u.tg_id}: {e}")
        
        await session.commit()

async def request_evening_logs(bot: Bot, user: User = None):
    """
    Sends evening log request to a specific user or all active users.
    """
    now = datetime.utcnow()
    
    async with get_db_session() as session:
        if user:
            users = [user]
        else:
            stmt = select(User).where(User.role == "client").options(joinedload(User.shadow_map))
            result = await session.execute(stmt)
            users = result.unique().scalars().all()
            
        for u in users:
            if not u.shadow_map: continue
            
            text = (
                "🌙 Время для вечернего Shadow Log.\n\n"
                "Как сегодня проявилось твое теневое качество? Какое сопротивление ты почувствовал(а)?\n\n"
                "Пришли текст или запиши голосовое сообщение."
            )
            try:
                await bot.send_message(u.tg_id, text)
                u.last_evening_sent = now
                logging.info(f"Evening request sent to {u.tg_id}")
            except Exception as e:
                logging.error(f"Failed to request evening from {u.tg_id}: {e}")
                
        await session.commit()

async def send_group_weekly_report(bot: Bot):
    """
    Generates and sends a summary report for the whole active group to admins.
    """
    logging.info("Generating group weekly report")
    async with get_db_session() as session:
        stmt = select(User).where(User.status == "active")
        result = await session.execute(stmt)
        users = result.scalars().all()
        
        if not users:
            logging.info("No active users for group report")
            return

        users_data = [
            {
                "name": u.full_name or str(u.tg_id),
                "sfi": round(u.sfi_index or 1.0, 2),
                "flags": u.red_flags_count or 0,
                "last_insight": u.last_insight or "N/A"
            }
            for u in users
        ]
        
        report = await generate_group_weekly_summary(users_data)
        report_text = f"👑 {hbold('WEEKLY GROUP SUMMARY')}\n\n{report}"
        
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(admin_id, report_text, parse_mode="HTML")
            except Exception as e:
                logging.error(f"Failed to send group report to admin {admin_id}: {e}")

async def send_weekly_briefings(bot: Bot):
    """
    Deprecated in favor of group summary, but kept for manual triggers if needed.
    """
    pass

async def dynamic_scheduler_job(bot: Bot):
    """
    Ticks every minute to check if any user needs a message based on their custom settings.
    """
    now = datetime.utcnow()
    current_time_str = now.strftime("%H:%M")
    today = now.date()
    
    async with get_db_session() as session:
        stmt = select(User).where(User.role == "client").options(joinedload(User.shadow_map))
        result = await session.execute(stmt)
        users = result.unique().scalars().all()
        
        for user in users:
            # Check morning
            if user.morning_time == current_time_str:
                last_sent = user.last_morning_sent.date() if user.last_morning_sent else None
                if last_sent != today:
                    await send_morning_impulse(bot, user)
            
            # Check evening
            if user.evening_time == current_time_str:
                last_sent = user.last_evening_sent.date() if user.last_evening_sent else None
                if last_sent != today:
                    await request_evening_logs(bot, user)

async def reload_admin_jobs(bot: Bot):
    """Reloads admin jobs with new times from DB."""
    global _scheduler
    if not _scheduler: return
    
    logging.info("Reloading admin jobs...")
    
    # Remove existing admin jobs
    for job_id in ["admin_morning", "admin_deadline", "admin_evening", "group_weekly_report"]:
        try: _scheduler.remove_job(job_id)
        except: pass
        
    async with get_db_session() as session:
        settings = await GlobalSettings.get_settings(session)
        
        # Helper to parse HH:MM
        def p(t):
            h, m = map(int, t.split(":"))
            return h, m
            
        h1, m1 = p(settings.morning_time)
        _scheduler.add_job(send_admin_morning_pulse, CronTrigger(hour=h1, minute=m1), args=[bot], id="admin_morning")
        
        h2, m2 = p(settings.deadline_time)
        _scheduler.add_job(send_admin_deadline_control, CronTrigger(hour=h2, minute=m2), args=[bot], id="admin_deadline")
        
        h3, m3 = p(settings.evening_time)
        _scheduler.add_job(send_admin_evening_concentrate, CronTrigger(hour=h3, minute=m3), args=[bot], id="admin_evening")
        
        h4, m4 = p(settings.sunday_time)
        _scheduler.add_job(send_group_weekly_report, CronTrigger(day_of_week='sun', hour=h4, minute=m4), args=[bot], id="group_weekly_report")

def setup_scheduler(bot: Bot):
    global _scheduler
    _scheduler = AsyncIOScheduler(timezone="UTC")
    
    # Run dynamic checker every minute
    _scheduler.add_job(
        dynamic_scheduler_job,
        IntervalTrigger(minutes=1),
        args=[bot],
        name="dynamic_scheduler",
        id="dynamic_scheduler"
    )
    
    # Initial load of admin jobs
    # We use a trick to run the async reload in the sync setup or just let the caller handle it.
    # But since setup_scheduler is called in main, we can make it async if needed.
    # For now, let's just use the default times for the first start or call it manually after start.
    
    return _scheduler
