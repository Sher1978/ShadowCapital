from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.markdown import hbold
from database.connection import get_db_session
from database.models import GlobalSettings
import re

settings_router = Router()

class SettingsState(StatesGroup):
    waiting_for_time = State()

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
        builder.adjust(2)
        
        await message.answer(text, reply_markup=builder.as_markup())

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
