from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.markdown import hbold
from database.connection import get_db_session
from database.models import GlobalSettings
import re

from config import ADMIN_IDS

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

@settings_router.message(F.text == "⚙️ Настройки")
async def settings_main_handler(message: types.Message):
    async with get_db_session() as session:
        settings = await GlobalSettings.get_settings(session)
        
        text = (
            f"⚙️ {hbold('Настройки уведомлений Shadow Advisor')}\n\n"
            f"📍 {hbold('Утренний скан:')} {settings.morning_time}\n"
            f"📍 {hbold('Контроль дедлайна:')} {settings.deadline_time}\n"
            f"📍 {hbold('Вечерний концентрат:')} {settings.evening_time}\n"
            f"📍 {hbold('Воскресная стратегия:')} {settings.sunday_time}\n\n"
            f"Нажми на кнопку ниже, чтобы изменить время (в формате ЧЧ:ММ)."
        )
        
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        builder = InlineKeyboardBuilder()
        builder.button(text="🌅 Утро", callback_data="set_time_morning")
        builder.button(text="🚩 Дедлайн", callback_data="set_time_deadline")
        builder.button(text="🧠 Вечер", callback_data="set_time_evening")
        builder.button(text="📊 Воскресенье", callback_data="set_time_sunday")
        
        if is_admin(message.from_user.id):
            builder.button(text="🌅 Утренний Импульс", callback_data="trigger_morning")
            builder.button(text="📝 Вечерний Лог", callback_data="trigger_evening")
            builder.button(text="📊 Итоги Недели", callback_data="trigger_weekly")
            
        builder.adjust(2)
        
        await message.answer(text, reply_markup=builder.as_markup())

@settings_router.callback_query(F.data.startswith("trigger_"))
async def trigger_manual_callback(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет прав администратора.", show_alert=True)
        return
        
    action = callback.data.replace("trigger_", "")
    from utils.scheduler import send_morning_impulse, send_weekly_briefings, request_evening_logs
    
    if action == "morning":
        await callback.message.answer("🚀 Запускаю рассылку утренних импульсов...")
        await send_morning_impulse(callback.bot)
    elif action == "evening":
        await callback.message.answer("📝 Запускаю сбор вечерних логов...")
        await request_evening_logs(callback.bot)
    elif action == "weekly":
        await callback.message.answer("📊 Запускаю рассылку итогов недели...")
        await send_weekly_briefings(callback.bot)
        
    await callback.answer("Запущено!")

@settings_router.callback_query(F.data.startswith("set_time_"))
async def set_time_callback_handler(callback: types.CallbackQuery, state: FSMContext):
    time_type = callback.data.replace("set_time_", "")
    await state.update_data(time_type=time_type)
    await state.set_state(SettingsState.waiting_for_time)
    
    names = {
        "morning": "Утреннего скана",
        "deadline": "Контроля дедлайна",
        "evening": "Вечернего концентрата",
        "sunday": "Воскресной стратегии"
    }
    
    await callback.message.answer(f"Введите новое время для {hbold(names[time_type])} в формате ЧЧ:ММ (например, 09:30):")
    await callback.answer()

@settings_router.message(SettingsState.waiting_for_time)
async def process_time_input(message: types.Message, state: FSMContext):
    new_time = message.text.strip()
    
    # Validation
    if not re.match(r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$", new_time):
        await message.answer("❌ Неверный формат. Пожалуйста, введите время как ЧЧ:ММ (например, 09:00 или 21:15).")
        return
        
    data = await state.get_data()
    time_type = data['time_type']
    
    async with get_db_session() as session:
        settings = await GlobalSettings.get_settings(session)
        if time_type == "morning": settings.morning_time = new_time
        elif time_type == "deadline": settings.deadline_time = new_time
        elif time_type == "evening": settings.evening_time = new_time
        elif time_type == "sunday": settings.sunday_time = new_time
        
        await session.commit()
    
    await state.clear()
    await message.answer(f"✅ Время обновлено на {hbold(new_time)}.")
    
    # Reload jobs (to be implemented in scheduler)
    from utils.scheduler import reload_admin_jobs
    await reload_admin_jobs(message.bot)
