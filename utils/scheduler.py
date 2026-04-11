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
from utils.timezone_utils import get_user_current_day

logger = logging.getLogger(__name__)

_scheduler = None

async def send_admin_morning_pulse(bot: Bot):
    """09:00 UTC: Notify admin about SFI levels."""
    users = await FirestoreDB.get_active_users()
    
    red_zone = [u for u in users if u.get("sfi_index", 1.0) > 0.7 or u.get("red_flags_count", 0) >= 3]
    
    text = (
        f"рџЊ‘ {hbold('Advisor, РІСЂРµРјСЏ СЃРєР°РЅРёСЂРѕРІР°РЅРёСЏ.')}\n\n"
        f"РЎРёСЃС‚РµРјР° РѕР±РЅРѕРІРёР»Р° РїРѕРєР°Р·Р°С‚РµР»Рё SFI. Р’ В«РєСЂР°СЃРЅРѕР№ Р·РѕРЅРµВ» СЃРµР№С‡Р°СЃ {hbold(len(red_zone))} С‡РµР».\n"
        f"РџСЂРѕРІРµСЂСЊ РґРµС‚Р°Р»Рё РІ СЂР°Р·РґРµР»Рµ `рџљЂ РЎРїСЂРёРЅС‚С‹`."
    )
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text="рџљЂ РЎРїСЂРёРЅС‚С‹", callback_data="active_page_0")
    
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
            missed.append(f"вЂў {u.get('full_name')} (@{u.get('username') or u.get('tg_id')})")
    
    if not missed:
        text = f"рџљ© {hbold('РљРѕРЅС‚СЂРѕР»СЊ РґРµРґР»Р°Р№РЅР°:')} Р’СЃРµ РѕС‚С‡РµС‚С‹ СЃРґР°РЅС‹ РІРѕРІСЂРµРјСЏ. РЎР°Р±РѕС‚Р°Р¶Р° РЅРµ РѕР±РЅР°СЂСѓР¶РµРЅРѕ."
    else:
        text = (
            f"рџљ© {hbold('Р’РЅРёРјР°РЅРёРµ: РЎР±РѕСЂ Р»РѕРіРѕРІ Р·Р°РІРµСЂС€РµРЅ.')}\n\n"
            f"Р­С‚Рё РїРѕР»СЊР·РѕРІР°С‚РµР»Рё РќР• СЃРґР°Р»Рё РѕС‚С‡РµС‚ РІРѕРІСЂРµРјСЏ:\n"
            + "\n".join(missed) + "\n\n"
            f"РЎРёСЃС‚РµРјР° РіРѕС‚РѕРІР° Рє Р°СѓРґРёС‚Сѓ РёРЅСЃР°Р№С‚РѕРІ."
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

    insights = [f"вЂў {hbold(u.get('full_name'))}: {u.get('last_insight')}" for u in users]
    
    text = (
        f"рџ§  {hbold('РЎРІРѕРґРєР° РёРЅСЃР°Р№С‚РѕРІ РіРѕС‚РѕРІР°.')}\n\n"
        + "\n".join(insights) + "\n\n"
        f"Р•СЃС‚СЊ Р»Рё РјРѕРјРµРЅС‚С‹ РґР»СЏ С‚РІРѕРµРіРѕ Р»РёС‡РЅРѕРіРѕ РІРјРµС€Р°С‚РµР»СЊСЃС‚РІР°?"
    )
    
    for admin_id in ADMIN_IDS:
        try: await bot.send_message(admin_id, text)
        except: pass

async def send_morning_impulse(bot: Bot, user: dict = None, bypass_audit: bool = False) -> int:
    """Sends morning impulse to a specific user or all active users. Returns count of sent messages."""
    now = datetime.now(timezone.utc)
    logger.info(f"рџЊ… [SCHEDULER] Starting send_morning_impulse. Manual trigger: {user is not None}")
    
    if user:
        users = [user]
    else:
        users = await FirestoreDB.get_active_users()
        
    logger.info(f"рџЊ… [SCHEDULER] Found {len(users)} active users for morning pulse.")
    
    count = 0
    sent_to_names = []
    last_text = None
    for u in users:
        u_id = u.get('tg_id')
        if not u_id: continue
        
        logger.debug(f"рџЊ… [SCHEDULER] Processing user {u_id} ({u.get('full_name')})")
        
        try:
            start_date = u.get('sprint_start_date') or u.get('created_at')
            if not start_date: 
                logger.warning(f"вљ пёЏ [SCHEDULER] User {u_id} has no start date")
                continue
            
            if isinstance(start_date, str):
                try: start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                except: continue
            
                        day = get_user_current_day(start_date, u.get('timezone', 'UTC+7'))
            
            # --- SHADOW CURRENCY AUDIT TRIGGER ---
            if not bypass_audit and day in [1, 7, 22]:
                existing_audit = await FirestoreDB.get_audit(u['id'], day)
                if not existing_audit:
                    logger.info(f"🗝 [AUDIT] Triggering Shadow Currency Audit for {u_id} (Day {day})")
                    audit_text = (
                        f"🔬 {hbold('SHADOW CURRENCY AUDIT: DAY ' + str(day))}\n\n"
                        "Для продолжения Спринта необходимо провести замер твоих жизненных активов.\n\n"
                        "Это залог твоей капитализации. Без данных мы летим вслепую.\n\n"
                        "Нажми кнопку ниже, чтобы начать."
                    )
                    from aiogram.utils.keyboard import InlineKeyboardBuilder
                    builder = InlineKeyboardBuilder()
                    builder.button(text="🗝 Начать аудит", callback_data="start_audit")
                    await bot.send_message(u_id, audit_text, reply_markup=builder.as_markup())
                    continue # Skip task delivery until audit is done
            try:
                task_data = await get_task_2_0(day, u.get('scenario_type') or "Sovereign")
                if not task_data:
                    # Fallback to old method or default
                    task_body = await get_daily_task_from_sheets(day, u.get('scenario_type') or "Sovereign")
                    theory = "РџСЂРѕРґРѕР»Р¶Р°РµРј РїРѕРіСЂСѓР¶РµРЅРёРµ РІ С‚РІРѕРµ С‚РµРЅРµРІРѕРµ РєР°С‡РµСЃС‚РІРѕ."
                    day_name = f"Р”РµРЅСЊ {day}"
                else:
                    theory = task_data['theory']
                    day_name = task_data['day_name']
                    task_body = None # We will send tasks after selection
            except RuntimeError as re:
                err_msg = f"вљ пёЏ [GSheets Error] Could not fetch morning task: {re}"
                logger.error(f"вќЊ {err_msg}")
                for admin_id in ADMIN_IDS:
                    try: await bot.send_message(admin_id, err_msg)
                    except: pass
                continue
            
            import random
            full_name = u.get('full_name', '')
            first_name = full_name.split()[0] if full_name else ""
            name_suffix = f", {first_name}" if first_name else ""

            greetings = [
                f"рџЊ… Р”РѕР±СЂРѕРµ СѓС‚СЂРѕ{name_suffix}!",
                f"вЂпёЏ РЎ РЅРѕРІС‹Рј РґРЅРµРј{name_suffix}!",
                f"вњЁ РџСЂРёРІРµС‚{name_suffix}!",
                f"рџ”Ґ РџСЂРµРєСЂР°СЃРЅРѕРµ СѓС‚СЂРѕ{name_suffix}!",
                f"рџЊџ Р”РѕР±СЂРѕРµ СѓС‚СЂРѕ{name_suffix}!"
            ]
            
            if task_body:
                # Fallback style
                quality = u.get('target_quality_l1') or u.get('target_quality') or 'РџСЂРѕСЂР°Р±РѕС‚РєР° РўРµРЅРё'
                text = (
                    f"{random.choice(greetings)}\n\n"
                    f"рџ’Ћ {hbold(quality)}: {day_name}\n\n"
                    f"{task_body}"
                )
                from aiogram.utils.keyboard import InlineKeyboardBuilder
                builder = InlineKeyboardBuilder()
                builder.button(text="вњ… Р“РѕС‚РѕРІ Рє РІС‹РїРѕР»РЅРµРЅРёСЋ", callback_data="morning_confirm")
                builder.button(text="рџ“ќ РЎРґР°С‚СЊ РѕС‚С‡РµС‚ СЃРµР№С‡Р°СЃ", callback_data="start_early_log")
                builder.adjust(1)
            else:
                # Task Engine 2.0 Style
                quality = u.get('target_quality_l1') or u.get('target_quality') or 'РџСЂРѕСЂР°Р±РѕС‚РєР° РўРµРЅРё'
                phase_text = f"{hitalic(task_data.get('phase'))}\n\n" if task_data.get('phase') else ""
                text = (
                    f"{random.choice(greetings)}\n\n"
                    f"рџ’Ћ {hbold(quality)}: {day_name}\n\n"
                    f"{phase_text}"
                    f"{theory or 'РџРѕСЂР° РїСЂРёСЃС‚СѓРїР°С‚СЊ Рє СЂР°Р±РѕС‚Рµ.'}\n\n"
                    f"Р’С‹Р±РµСЂРё СѓСЂРѕРІРµРЅСЊ СЃР»РѕР¶РЅРѕСЃС‚Рё РЅР° СЃРµРіРѕРґРЅСЏ:"
                )
                from aiogram.utils.keyboard import InlineKeyboardBuilder
                builder = InlineKeyboardBuilder()
                builder.button(text="в—ЅпёЏ Light", callback_data="task_level:light")
                builder.button(text="рџ”¶ Medium", callback_data="task_level:medium")
                builder.button(text="рџ”Ґ Hard", callback_data="task_level:hard")
                builder.adjust(3)
            
            last_text = text
            await bot.send_message(u_id, text, reply_markup=builder.as_markup())
            await FirestoreDB.update_user(u['id'], {"last_morning_sent": now})
            logger.info(f"вњ… [SCHEDULER] Morning impulse sent to {u_id}")
            count += 1
            sent_to_names.append(u.get('full_name', f"ID: {u_id}"))
        except Exception as e:
            logger.error(f"вќЊ [SCHEDULER] Failed to process morning for {u_id}: {e}")
            
    summary = f"рџЊ… [SCHEDULER] Р Р°СЃСЃС‹Р»РєР° Р·Р°РІРµСЂС€РµРЅР°. РћС‚РїСЂР°РІР»РµРЅРѕ: {count} С‡РµР»."
    if count > 0:
        summary += f" ({', '.join(sent_to_names)})"
    if count > 0 and last_text:
        # Extract the task text part for brevity or send full message?
        # The user wants "С‚РµРєСЃС‚ РѕС‚РїСЂР°РІР»РµРЅРЅРѕРіРѕ СЃРѕРѕР±С‰РµРЅРёСЏ", so I'll send the full text
        summary += f"\n\nрџ“‹ {hbold('РўРµРєСЃС‚ СЃРѕРѕР±С‰РµРЅРёСЏ:')}\n---\n{last_text}"
        
    for admin_id in ADMIN_IDS:
        try: await bot.send_message(admin_id, summary)
        except Exception as e:
            logger.error(f"вќЊ Failed to send summary to admin {admin_id}: {e}")
            
    logger.info(f"рџЊ… [SCHEDULER] Finished. Total sent: {count}")
    return count

async def request_evening_logs(bot: Bot, user: dict = None) -> int:
    """Sends evening log request to a specific user or all active users. Returns count sent."""
    now = datetime.now(timezone.utc)
    logger.info(f"рџЊ™ [SCHEDULER] Starting request_evening_logs. Manual: {user is not None}")
    
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
                
                        day = get_user_current_day(start_date, u.get('timezone', 'UTC+7'))
            
            # --- SHADOW CURRENCY AUDIT TRIGGER ---
            if not bypass_audit and day in [1, 7, 22]:
                existing_audit = await FirestoreDB.get_audit(u['id'], day)
                if not existing_audit:
                    logger.info(f"🗝 [AUDIT] Triggering Shadow Currency Audit for {u_id} (Day {day})")
                    audit_text = (
                        f"🔬 {hbold('SHADOW CURRENCY AUDIT: DAY ' + str(day))}\n\n"
                        "Для продолжения Спринта необходимо провести замер твоих жизненных активов.\n\n"
                        "Это залог твоей капитализации. Без данных мы летим вслепую.\n\n"
                        "Нажми кнопку ниже, чтобы начать."
                    )
                    from aiogram.utils.keyboard import InlineKeyboardBuilder
                    builder = InlineKeyboardBuilder()
                    builder.button(text="🗝 Начать аудит", callback_data="start_audit")
                    await bot.send_message(u_id, audit_text, reply_markup=builder.as_markup())
                    continue # Skip task delivery until audit is done
            try:
                task_data = await get_task_2_0(day, u.get('scenario_type') or "Sovereign")
                if task_data and task_data.get('evening_report'):
                    questions_text = task_data['evening_report']
                else:
                    questions_text = await get_evening_question_from_sheets(day, u.get('scenario_type') or "Sovereign")
            except RuntimeError as re:
                err_msg = f"вљ пёЏ [GSheets Error] Could not fetch evening questions: {re}"
                logger.error(f"вќЊ {err_msg}")
                for admin_id in ADMIN_IDS:
                    try: await bot.send_message(admin_id, err_msg)
                    except: pass
                continue
                
            if not questions_text:
                questions_text = (
                    "рџ’Ў Р’СЃРїРѕРјРЅРё СЃРµРіРѕРґРЅСЏС€РЅРёР№ РґРµРЅСЊ:\n\n"
                    "вќ“ РљРђРљ РЎР•Р“РћР”РќРЇ РџР РћРЇР’РР›РћРЎР¬ РўР’РћР• РўР•РќР•Р’РћР• РљРђР§Р•РЎРўР’Рћ?\n\n"
                    "вќ“ РљРђРљРћР• РЎРћРџР РћРўРР’Р›Р•РќРР• РўР« РџРћР§РЈР’РЎРўР’РћР’РђР›(Рђ)?\n\n"
                    "рџЋ¤ РџСЂРёС€Р»Рё С‚РµРєСЃС‚ РёР»Рё Р·Р°РїРёС€Рё РіРѕР»РѕСЃРѕРІРѕРµ СЃРѕРѕР±С‰РµРЅРёРµ."
                )
            
            text = (
                f"рџЊ™ {hbold('РџСЂРёС€Р»Рѕ РІСЂРµРјСЏ РґР»СЏ Р’РµС‡РµСЂРЅРµРіРѕ РћС‚С‡РµС‚Р°.')} (Р”РµРЅСЊ {day})\n\n"
                f"{questions_text}\n\n"
                f"рџЋ¤ РџСЂРёС€Р»Рё С‚РµРєСЃС‚ РёР»Рё Р·Р°РїРёС€Рё РіРѕР»РѕСЃРѕРІРѕРµ СЃРѕРѕР±С‰РµРЅРёРµ."
            )
            from aiogram.utils.keyboard import InlineKeyboardBuilder
            builder = InlineKeyboardBuilder()
            builder.button(text="рџ“ќ Р—Р°РїРѕР»РЅРёС‚СЊ РѕС‚С‡РµС‚", callback_data="start_evening_log")
            builder.button(text="вљ™пёЏ РР·РјРµРЅРёС‚СЊ РІСЂРµРјСЏ РґРѕСЃС‚Р°РІРєРё", callback_data="edit_delivery_times")
            builder.adjust(1)
            
            await bot.send_message(u_id, text, reply_markup=builder.as_markup())
            await FirestoreDB.update_user(u['id'], {"last_evening_sent": now})
            logger.info(f"вњ… [SCHEDULER] Evening request sent to {u_id}")
            count += 1
        except Exception as e:
            logger.error(f"вќЊ [SCHEDULER] Failed to send evening to {u_id}: {e}")
            
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
    report_text = f"рџ‘‘ {hbold('WEEKLY GROUP SUMMARY')}\n\n{report}"
    
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
            # logger.debug(f"рџ¤« [SCHEDULER] Quiet hours for user {user.get('tg_id')}. Skipping pulses.")
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
        
    logging.info("вЏі Fetching global settings from Firestore...")
    settings = await FirestoreDB.get_global_settings()
    logging.info(f"вњ… Global settings fetched: {settings.keys()}")
    
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

