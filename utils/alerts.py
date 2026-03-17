from aiogram import Bot, types
from aiogram.utils.markdown import hbold, hitalic
from config import ADMIN_IDS
import logging

async def send_red_alert(bot: Bot, user_full_name: str, user_tg_id: int, marker: str, reason: str, content: str):
    """
    Sends a Red Alert to all admins when sabotage is detected.
    """
    text = (
        f"🚨 {hbold('RED ALERT: ОБНАРУЖЕН САБОТАЖ')} 🚨\n\n"
        f"👤 {hbold('Клиент:')} {user_full_name} ({user_tg_id})\n"
        f"⚠️ {hbold('Маркер:')} {marker.upper()}\n"
        f"📝 {hbold('Причина:')} {reason}\n\n"
        f"💬 {hbold('Текст отчета:')}\n{hitalic(content)}"
    )
    
    # Inline button to reply to client
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="💬 Ответить клиенту", callback_data=f"ai_reply_{user_tg_id}")]
    ])
    
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, text, reply_markup=keyboard)
        except Exception as e:
            logging.error(f"Failed to send Red Alert to {admin_id}: {e}")
