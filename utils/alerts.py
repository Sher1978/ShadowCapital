from aiogram import Bot, types
from aiogram.utils.markdown import hbold, hitalic
from config import ADMIN_IDS
import logging

async def send_red_alert(bot: Bot, user_full_name: str, user_tg_id: int, marker: str, reason: str, content: str):
    """
    Sends a Red Alert to all admins when sabotage is detected.
    """
    text = (
        f"рџљЁ {hbold('RED ALERT: РћР‘РќРђР РЈР–Р•Рќ РЎРђР‘РћРўРђР–')} рџљЁ\n\n"
        f"рџ‘¤ {hbold('РљР»РёРµРЅС‚:')} {user_full_name} ({user_tg_id})\n"
        f"⚠️ {hbold('РњР°СЂРєРµСЂ:')} {marker.upper()}\n"
        f"рџ“ќ {hbold('РџСЂРёС‡РёРЅР°:')} {reason}\n\n"
        f"💬 {hbold('РўРµРєСЃС‚ РѕС‚С‡РµС‚Р°:')}\n{hitalic(content)}"
    )
    
    # Inline button to reply to client
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="💬 РћС‚РІРµС‚РёС‚СЊ РєР»РёРµРЅС‚Сѓ", callback_data=f"ai_reply_{user_tg_id}")]
    ])
    
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, text, reply_markup=keyboard)
        except Exception as e:
            logging.error(f"Failed to send Red Alert to {admin_id}: {e}")

async def send_audit_report(bot: Bot, user: dict, audit_data: dict, day: int):
    """
    Sends a currency audit report to all admins.
    Day 22 logic included for delta calculation.
    """
    from database.firebase_db import FirestoreDB
    
    # Delta calculation for Day 22
    delta_text = ""
    if day == 22:
        baseline = await FirestoreDB.get_audit_baseline(user['id'])
        if baseline:
            m_delta = audit_data['money'] - baseline['money']
            t_delta = audit_data['time'] - baseline['time']
            s_delta = audit_data['status'] - baseline['status']
            d_delta = audit_data['drive'] - baseline['drive']
            
            def fmt(val): return f"+{val}" if val > 0 else str(val)
            
            delta_text = (
                f"\n\n📈 {hbold('ДИНАМИКА (vs День 1):')}\n"
                f"Money: {fmt(m_delta)} | Time: {fmt(t_delta)}\n"
                f"Status: {fmt(s_delta)} | Drive: {fmt(d_delta)}"
            )

    text = (
        f"🗝 {hbold('SHADOW CURRENCY AUDIT: DAY ' + str(day))}\n\n"
        f"👤 {hbold('Клиент:')} {user.get('full_name')} (@{user.get('username') or 'N/A'})\n\n"
        f"💰 Money: {hbold(audit_data['money'])}/10\n"
        f"⏳ Time: {hbold(audit_data['time'])}/10\n"
        f"👑 Status: {hbold(audit_data['status'])}/10\n"
        f"🔋 Drive: {hbold(audit_data['drive'])}/10\n\n"
        f"🎯 {hbold('Фокус:')} {audit_data['focus_currency']}"
        f"{delta_text}"
    )

    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, text)
        except Exception as e:
            logging.error(f"Failed to send Audit Alert to {admin_id}: {e}")
