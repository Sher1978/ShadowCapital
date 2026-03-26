from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from aiogram import Bot
from database.firebase_db import FirestoreDB
from datetime import datetime, timezone
import logging
import re
from config import ADMIN_IDS
from utils.analysis import generate_weekly_briefing, generate_group_weekly_summary
from utils.gsheets_api import get_daily_task_from_sheets, get_evening_question_from_sheets, get_task_2_0
from aiogram.utils.markdown import hbold, hitalic

logger = logging.getLogger(__name__)

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
    builder.button(text="🚀 Спринты", callback_data="active_page_0")
    
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
    from database.firebase_db import Query
    # Get top 5 active users with highest SFI who have an insight
    query = FirestoreDB.db.collection("users") \
             .where("status", "==", "active") \
             .order_by("sfi_index", direction=Query.DESCENDING) \
             .limit(20)
    docs = query.stream()
    
    users = []
    async for doc in docs:
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

async def send_morning_impulse(bot: Bot, user: dict = None) -> int:
    """Sends morning impulse to a specific user or all active users. Returns count of sent messages."""
    now = datetime.now(timezone.utc)
    logger.info(f"🌅 [SCHEDULER] Starting send_morning_impulse. Manual trigger: {user is not None}")
    
    if user:
        users = [user]
    else:
        users = await FirestoreDB.get_active_users()
        
    logger.info(f"🌅 [SCHEDULER] Found {len(users)} active users for morning pulse.")
    
    count = 0
    sent_to_names = []
    last_text = None
    for u in users:
        u_id = u.get('tg_id')
        if not u_id: continue
        
        logger.debug(f"🌅 [SCHEDULER] Processing user {u_id} ({u.get('full_name')})")
        
        try:
            start_date = u.get('sprint_start_date') or u.get('created_at')
            if not start_date: 
                logger.warning(f"⚠️ [SCHEDULER] User {u_id} has no start date")
                continue
            
            if isinstance(start_date, str):
                try: start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                except: continue
            
            day = (now - start_date).days + 1
            try:
                task_data = await get_task_2_0(day, u.get('scenario_type') or "Sovereign")
                if not task_data:
                    # Fallback to old method or default
                    task_body = await get_daily_task_from_sheets(day, u.get('scenario_type') or "Sovereign")
                    theory = "Продолжаем погружение в твое теневое качество."
                    day_name = f"День {day}"
                else:
                    theory = task_data['theory']
                    day_name = task_data['day_name']
                    task_body = None # We will send tasks after selection
            except RuntimeError as re:
                err_msg = f"⚠️ [GSheets Error] Could not fetch morning task: {re}"
                logger.error(f"❌ {err_msg}")
                for admin_id in ADMIN_IDS:
                    try: await bot.send_message(admin_id, err_msg)
                    except: pass
                break
            
            import random
            full_name = u.get('full_name', '')
            first_name = full_name.split()[0] if full_name else ""
            name_suffix = f", {first_name}" if first_name else ""

            greetings = [
                f"🌅 Доброе утро{name_suffix}!",
                f"☀️ С новым днем{name_suffix}!",
                f"✨ Привет{name_suffix}!",
                f"🔥 Прекрасное утро{name_suffix}!",
                f"🌟 Доброе утро{name_suffix}!"
            ]
            
            if task_body:
                # Fallback style
                quality = u.get('target_quality_l1') or u.get('target_quality') or 'Проработка Тени'
                text = (
                    f"{random.choice(greetings)}\n\n"
                    f"💎 {hbold(quality)}: {day_name}\n\n"
                    f"{task_body}"
                )
                from aiogram.utils.keyboard import InlineKeyboardBuilder
                builder = InlineKeyboardBuilder()
                builder.button(text="✅ Готов к выполнению", callback_data="morning_confirm")
                builder.button(text="📝 Сдать отчет сейчас", callback_data="start_early_log")
                builder.adjust(1)
            else:
                # Task Engine 2.0 Style
                quality = u.get('target_quality_l1') or u.get('target_quality') or 'Проработка Тени'
                phase_text = f"{hitalic(task_data.get('phase'))}\n\n" if task_data.get('phase') else ""
                text = (
                    f"{random.choice(greetings)}\n\n"
                    f"💎 {hbold(quality)}: {day_name}\n\n"
                    f"{phase_text}"
                    f"{theory or 'Пора приступать к работе.'}\n\n"
                    f"Выбери уровень сложности на сегодня:"
                )
                from aiogram.utils.keyboard import InlineKeyboardBuilder
                builder = InlineKeyboardBuilder()
                builder.button(text="◽️ Light", callback_data="task_level:light")
                builder.button(text="🔶 Medium", callback_data="task_level:medium")
                builder.button(text="🔥 Hard", callback_data="task_level:hard")
                builder.adjust(3)
            
            last_text = text
            await bot.send_message(u_id, text, reply_markup=builder.as_markup())
            await FirestoreDB.update_user(u['id'], {"last_morning_sent": now})
            logger.info(f"✅ [SCHEDULER] Morning impulse sent to {u_id}")
            count += 1
            sent_to_names.append(u.get('full_name', f"ID: {u_id}"))
        except Exception as e:
            logger.error(f"❌ [SCHEDULER] Failed to process morning for {u_id}: {e}")
            
    summary = f"🌅 [SCHEDULER] Рассылка завершена. Отправлено: {count} чел."
    if count > 0:
        summary += f" ({', '.join(sent_to_names)})"
    if count > 0 and last_text:
        # Extract the task text part for brevity or send full message?
        # The user wants "текст отправленного сообщения", so I'll send the full text
        summary += f"\n\n📋 {hbold('Текст сообщения:')}\n---\n{last_text}"
        
    for admin_id in ADMIN_IDS:
        try: await bot.send_message(admin_id, summary)
        except Exception as e:
            logger.error(f"❌ Failed to send summary to admin {admin_id}: {e}")
            
    logger.info(f"🌅 [SCHEDULER] Finished. Total sent: {count}")
    return count

async def request_evening_logs(bot: Bot, user: dict = None) -> int:
    """Sends evening log request to a specific user or all active users. Returns count sent."""
    now = datetime.now(timezone.utc)
    logger.info(f"🌙 [SCHEDULER] Starting request_evening_logs. Manual: {user is not None}")
    
    if user:
        users = [user]
    else:
        users = await FirestoreDB.get_active_users()
        
    count = 0
    for u in users:
        u_id = u.get('tg_id')
        if not u_id: continue
        
        try:
            start_date = u.get('sprint_start_date') or u.get('created_at')
            if not start_date: continue
            if isinstance(start_date, str):
                try: start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                except: continue
                
            day = (now - start_date).days + 1
            try:
                task_data = await get_task_2_0(day, u.get('scenario_type') or "Sovereign")
                if task_data and task_data.get('evening_report'):
                    questions_text = task_data['evening_report']
                else:
                    questions_text = await get_evening_question_from_sheets(day, u.get('scenario_type') or "Sovereign")
            except RuntimeError as re:
                err_msg = f"⚠️ [GSheets Error] Could not fetch evening questions: {re}"
                logger.error(f"❌ {err_msg}")
                for admin_id in ADMIN_IDS:
                    try: await bot.send_message(admin_id, err_msg)
                    except: pass
                break
                
            if not questions_text:
                questions_text = (
                    "💡 Вспомни сегодняшний день:\n\n"
                    "❓ КАК СЕГОДНЯ ПРОЯВИЛОСЬ ТВОЕ ТЕНЕВОЕ КАЧЕСТВО?\n\n"
                    "❓ КАКОЕ СОПРОТИВЛЕНИЕ ТЫ ПОЧУВСТВОВАЛ(А)?\n\n"
                    "🎤 Пришли текст или запиши голосовое сообщение."
                )
            
            text = (
                f"🌙 {hbold('Пришло время для Вечернего Отчета.')} (День {day})\n\n"
                f"{questions_text}\n\n"
                f"🎤 Пришли текст или запиши голосовое сообщение."
            )
            from aiogram.utils.keyboard import InlineKeyboardBuilder
            builder = InlineKeyboardBuilder()
            builder.button(text="📝 Заполнить отчет", callback_data="start_evening_log")
            builder.button(text="⚙️ Изменить время доставки", callback_data="edit_delivery_times")
            builder.adjust(1)
            
            await bot.send_message(u_id, text, reply_markup=builder.as_markup())
            await FirestoreDB.update_user(u['id'], {"last_evening_sent": now})
            logger.info(f"✅ [SCHEDULER] Evening request sent to {u_id}")
            count += 1
        except Exception as e:
            logger.error(f"❌ [SCHEDULER] Failed to send evening to {u_id}: {e}")
            
    return count

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

def get_timezone_offset(tz_str: str) -> int:
    """Parses 'UTC+X' or 'UTC-X' strings into integer offset. Returns 7 as default."""
    if not tz_str: return 7
    try:
        # Extract the number part, handling both + and -
        match = re.search(r'([+-]?\d+)', tz_str)
        if match:
            return int(match.group(1))
    except:
        pass
    return 7

def is_quiet_hours(local_time: datetime) -> bool:
    """Quiet hours: 23:00 to 08:00."""
    return local_time.hour >= 23 or local_time.hour < 8

async def dynamic_scheduler_job(bot: Bot):
    """Ticks every minute to check if any user needs a message based on their custom settings."""
    now = datetime.now(timezone.utc)
    
    users = await FirestoreDB.get_active_users()
    
    for user in users:
        # Timezone-aware check
        user_tz_str = user.get('timezone', 'UTC+7')
        offset = get_timezone_offset(user_tz_str)
            
        from datetime import timedelta
        user_local_time = now + timedelta(hours=offset)
        user_time_str = user_local_time.strftime("%H:%M")

        # Check Quiet Hours - safety net
        if is_quiet_hours(user_local_time):
            # logger.debug(f"🤫 [SCHEDULER] Quiet hours for user {user.get('tg_id')}. Skipping pulses.")
            continue

        today = user_local_time.date()

        # Check morning
        user_morning_time = user.get("morning_time") or "09:00"
        if user_morning_time == user_time_str:
            last_sent_dt = user.get("last_morning_sent")
            # Convert last_sent_dt to local date for comparison
            last_sent_date = (last_sent_dt + timedelta(hours=offset)).date() if last_sent_dt else None
            
            if last_sent_date != today:
                await send_morning_impulse(bot, user)
        
        # Check evening
        user_evening_time = user.get("evening_time") or "21:30"
        if user_evening_time == user_time_str:
            last_sent_dt = user.get("last_evening_sent")
            last_sent_date = (last_sent_dt + timedelta(hours=offset)).date() if last_sent_dt else None
            
            if last_sent_date != today:
                await request_evening_logs(bot, user)

async def reload_admin_jobs(bot: Bot):
    """Reloads admin jobs with new times from DB."""
    global _scheduler
    if not _scheduler: return
    
    logging.info("Reloading admin jobs...")
    
    for job_id in ["admin_morning", "admin_deadline", "admin_evening", "group_weekly_report"]:
        try: _scheduler.remove_job(job_id)
        except: pass
        
    logging.info("⏳ Fetching global settings from Firestore...")
    settings = await FirestoreDB.get_global_settings()
    logging.info(f"✅ Global settings fetched: {settings.keys()}")
    
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
