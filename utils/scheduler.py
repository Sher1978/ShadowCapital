from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from aiogram import Bot
from database.firebase_db import FirestoreDB
from datetime import datetime, timezone
import logging
from config import ADMIN_IDS
from utils.analysis import generate_weekly_briefing, generate_group_weekly_summary
from utils.gsheets_api import get_daily_task_from_sheets, get_evening_question_from_sheets
from aiogram.utils.markdown import hbold

_scheduler = None

async def send_admin_morning_pulse(bot: Bot):
    """09:00 UTC: Notify admin about SFI levels."""
    users = await FirestoreDB.get_active_users()
    
    red_zone = [u for u in users if u.get("sfi_index", 1.0) > 0.7 or u.get("red_flags_count", 0) >= 3]
    
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
    users = await FirestoreDB.get_active_users()
    today = datetime.now(timezone.utc).date()
    
    missed = []
    for u in users:
        logs = await FirestoreDB.get_logs(u['id'], limit=1)
        last_log = logs[0] if logs else None
        if not last_log or last_log.get('created_at').date() < today:
            missed.append(f"• {u.get('full_name')} (@{u.get('username') or u.get('tg_id')})")
    
    if not missed:
        text = f"🚩 {hbold('Контроль дедлайна:')} Все отчеты сданы вовремя. Саботажа не обнаружено."
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
    # Get top 5 active users with highest SFI who have an insight
    docs = FirestoreDB.db.collection("users") \
             .where("status", "==", "active") \
             .order_by("sfi_index", direction=FirestoreDB.firestore.Query.DESCENDING) \
             .limit(20).stream()
    
    users = []
    for doc in docs:
        d = doc.to_dict()
        if d.get("last_insight"):
            users.append(d)
        if len(users) >= 5:
            break
            
    if not users: return

    insights = [f"• {hbold(u.get('full_name'))}: {u.get('last_insight')}" for u in users]
    
    text = (
        f"🧠 {hbold('Сводка инсайтов готова.')}\n\n"
        + "\n".join(insights) + "\n\n"
        f"Есть ли моменты для твоего личного вмешательства?"
    )
    
    for admin_id in ADMIN_IDS:
        try: await bot.send_message(admin_id, text)
        except: pass

async def send_morning_impulse(bot: Bot, user: dict = None):
    """Sends morning impulse to a specific user or all active users."""
    now = datetime.now(timezone.utc)
    
    if user:
        users = [user]
    else:
        users = await FirestoreDB.get_active_users()
        
    for u in users:
        # Calculate day
        start_date = u.get('sprint_start_date') or u.get('created_at')
        if not start_date: continue
        
        # Determine if start_date is already a datetime (Firestore) or needs conversion
        if isinstance(start_date, str):
            try: start_date = datetime.fromisoformat(start_date)
            except: continue
        
        day = (now - start_date).days + 1
        
        # Fetch from Sheets
        task_body = await get_daily_task_from_sheets(day, u.get('scenario_type') or "Sovereign")
        if not task_body:
            task_body = "Продолжай интеграцию твоего качества. Хранитель сегодня спокоен."
        
        import random
        greetings = [
            "🌅 Доброе утро! Сегодня идеальный день, чтобы стать еще сильнее.",
            "☀️ С новым днем! Твой прогресс вдохновляет, продолжаем движение.",
            "✨ Привет! Сегодня — еще один шаг к твоему идеальному качеству. Вперед!",
            "🔥 Прекрасное утро, чтобы бросить вызов Хранителю и победить.",
            "🌟 Доброе утро! Твоя энергия сегодня — ключ к новым вершинам."
        ]
        greeting = random.choice(greetings)
        
        text = (
            f"{greeting}\n\n"
            f"💎 {hbold(u.get('target_quality_l1'))}: Утренний Импульс (День {day})\n\n"
            f"{task_body}\n\n"
            f"Помни про обход Хранителя — действуй мягко."
        )
        
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        builder = InlineKeyboardBuilder()
        builder.button(text="✅ Готов к выполнению", callback_data="morning_confirm")
        
        try:
            await bot.send_message(u.get('tg_id'), text, reply_markup=builder.as_markup())
            await FirestoreDB.update_user(u['id'], {"last_morning_sent": now})
            logging.info(f"Morning impulse sent to {u.get('tg_id')}")
        except Exception as e:
            logging.error(f"Failed to send morning to {u.get('tg_id')}: {e}")

async def request_evening_logs(bot: Bot, user: dict = None):
    """Sends evening log request to a specific user or all active users."""
    now = datetime.now(timezone.utc)
    
    if user:
        users = [user]
    else:
        users = await FirestoreDB.get_active_users()
        
    for u in users:
        # Calculate day
        start_date = u.get('sprint_start_date') or u.get('created_at')
        if not start_date: continue
        
        if isinstance(start_date, str):
            try: start_date = datetime.fromisoformat(start_date)
            except: continue
            
        day = (now - start_date).days + 1
        
        # Fetch dynamic questions from Sheets
        questions_text = await get_evening_question_from_sheets(day, u.get('scenario_type') or "Sovereign")
        
        if not questions_text:
            questions_text = (
                "Как сегодня проявилось твое теневое качество? Какое сопротивление ты почувствовал(а)?\n\n"
                "Пришли текст или запиши голосовое сообщение."
            )
        
        text = (
            f"🌙 {hbold('Время для вечернего Shadow Log.')}\n\n"
            f"{questions_text}"
        )
        try:
            await bot.send_message(u.get('tg_id'), text)
            await FirestoreDB.update_user(u['id'], {"last_evening_sent": now})
            logging.info(f"Evening request sent to {u.get('tg_id')}")
        except Exception as e:
            logging.error(f"Failed to request evening from {u.get('tg_id')}: {e}")

async def send_group_weekly_report(bot: Bot):
    """Generates and sends a summary report for the whole active group to admins."""
    logging.info("Generating group weekly report")
    users = await FirestoreDB.get_active_users()
    
    if not users:
        logging.info("No active users for group report")
        return

    users_data = [
        {
            "name": u.get("full_name") or str(u.get("tg_id")),
            "sfi": round(u.get("sfi_index", 1.0), 2),
            "flags": u.get("red_flags_count", 0),
            "last_insight": u.get("last_insight") or "N/A"
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
    pass

async def dynamic_scheduler_job(bot: Bot):
    """Ticks every minute to check if any user needs a message based on their custom settings."""
    now = datetime.now(timezone.utc)
    current_time_str = now.strftime("%H:%M")
    today = now.date()
    
    users = await FirestoreDB.get_active_users()
    
    for user in users:
        # Timezone-aware check
        user_tz_str = user.get('timezone', 'UTC+3')
        try:
            # Parse "UTC+X" or "UTC-X"
            offset = int(user_tz_str.replace("UTC", "").replace("+", ""))
        except:
            offset = 3
            
        from datetime import timedelta
        user_local_time = now + timedelta(hours=offset)
        user_time_str = user_local_time.strftime("%H:%M")

        # Check morning
        user_morning_time = user.get("morning_time") or "09:00"
        if user_morning_time == user_time_str:
            last_sent_dt = user.get("last_morning_sent")
            last_sent = last_sent_dt.date() if last_sent_dt else None
            if last_sent != today:
                await send_morning_impulse(bot, user)
        
        # Check evening
        user_evening_time = user.get("evening_time") or "21:30"
        if user_evening_time == user_time_str:
            last_sent_dt = user.get("last_evening_sent")
            last_sent = last_sent_dt.date() if last_sent_dt else None
            if last_sent != today:
                await request_evening_logs(bot, user)

async def reload_admin_jobs(bot: Bot):
    """Reloads admin jobs with new times from DB."""
    global _scheduler
    if not _scheduler: return
    
    logging.info("Reloading admin jobs...")
    
    for job_id in ["admin_morning", "admin_deadline", "admin_evening", "group_weekly_report"]:
        try: _scheduler.remove_job(job_id)
        except: pass
        
    settings = await FirestoreDB.get_global_settings()
    
    def p(t):
        try:
            h, m = map(int, t.split(":"))
            return h, m
        except:
            return 9, 0 # Fallback
        
    h1, m1 = p(settings.get("morning_time", "09:00"))
    _scheduler.add_job(send_admin_morning_pulse, CronTrigger(hour=h1, minute=m1), args=[bot], id="admin_morning")
    
    h2, m2 = p(settings.get("deadline_time", "20:30"))
    _scheduler.add_job(send_admin_deadline_control, CronTrigger(hour=h2, minute=m2), args=[bot], id="admin_deadline")
    
    h3, m3 = p(settings.get("evening_time", "21:30"))
    _scheduler.add_job(send_admin_evening_concentrate, CronTrigger(hour=h3, minute=m3), args=[bot], id="admin_evening")
    
    h4, m4 = p(settings.sunday_time if hasattr(settings, 'sunday_time') else "18:00") # Fixed logic
    # Actually settings is a dict from get_global_settings
    h4, m4 = p(settings.get("sunday_time", "18:00"))
    _scheduler.add_job(send_group_weekly_report, CronTrigger(day_of_week='sun', hour=h4, minute=m4), args=[bot], id="group_weekly_report")

def setup_scheduler(bot: Bot):
    global _scheduler
    _scheduler = AsyncIOScheduler(timezone="UTC")
    
    _scheduler.add_job(
        dynamic_scheduler_job,
        IntervalTrigger(minutes=1),
        args=[bot],
        name="dynamic_scheduler",
        id="dynamic_scheduler"
    )
    
    return _scheduler
