from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.markdown import hbold
from database.firebase_db import FirestoreDB
import re

import logging
from config import ADMIN_IDS, is_admin
from bot.states import SettingsState, ClientSettings
from bot.keyboards.builders import get_main_keyboard, get_navigation_keyboard

logger = logging.getLogger(__name__)

settings_router = Router()

@settings_router.message(F.text == "⚙️ Настройки")
@settings_router.message(F.text.contains("Настройки"))
async def settings_main_handler(message: types.Message):
    if is_admin(message.from_user.id):
        return await admin_settings_handler(message)
    else:
        return await client_settings_handler(message)

async def admin_settings_handler(message: types.Message):
    settings = await FirestoreDB.get_global_settings()
    
    text = (
        f"⚙️ {hbold('Настройки уведомлений Shadow Advisor')}\n\n"
        f"📍 {hbold('Утренний скан:')} {settings.get('morning_time', '09:00')}\n"
        f"📍 {hbold('Контроль дедлайна:')} {settings.get('deadline_time', '20:30')}\n"
        f"📍 {hbold('Вечерний концентрат:')} {settings.get('evening_time', '21:30')}\n"
        f"📍 {hbold('Воскресная стратегия:')} {settings.get('sunday_time', '18:00')}\n\n"
        f"Нажми на кнопку ниже, чтобы изменить время (в формате ЧЧ:ММ). Все изменения применяются глобально."
    )
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text="🌅 Утро", callback_data="set_time_morning")
    builder.button(text="🚩 Дедлайн", callback_data="set_time_deadline")
    builder.button(text="🧠 Вечер", callback_data="set_time_evening")
    builder.button(text="📊 Воскресенье", callback_data="set_time_sunday")
    
    builder.button(text="🚀 Запустить Утро", callback_data="trigger_morning")
    builder.button(text="📝 Запросить Отчеты", callback_data="trigger_evening")
    builder.button(text="📊 Итоги Недели", callback_data="trigger_weekly")
        
    builder.adjust(2)
    
    await message.answer(text, reply_markup=builder.as_markup())

async def client_settings_handler(message: types.Message):
    user = await FirestoreDB.get_user(message.from_user.id)
    if not user:
        return await message.answer("❌ Ошибка: профиль не найден.")

    text = (
        f"👤 {hbold('Мой Профиль')}\n\n"
        f"🆔 {hbold('ID:')} {user.get('tg_id')}\n"
        f"👤 {hbold('Имя:')} {user.get('full_name')}\n"
        f"🌍 {hbold('Часовой пояс:')} {user.get('timezone', 'UTC+0')}\n"
        f"💎 {hbold('Качество (L1):')} {user.get('target_quality_l1') or 'Не задано'}\n"
        f"🎬 {hbold('Сценарий:')} {user.get('scenario_type') or 'Не задан'}\n\n"
        f"Ты можешь изменить свое имя или часовой пояс. Данные спринта (качество/сценарий) меняются только администратором."
    )
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text="✏️ Изменить Имя", callback_data="client_edit_name")
    builder.button(text="🌍 Изменить Часовой Пояс", callback_data="client_edit_tz")
    builder.button(text="⚙️ Настроить время доставки", callback_data="edit_delivery_times")
    builder.adjust(1)
    
    await message.answer(text, reply_markup=builder.as_markup())

# --- Client Settings Handlers ---

@settings_router.callback_query(F.data == "client_edit_name")
async def client_edit_name_start(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(ClientSettings.waiting_for_edit_name)
    await callback.message.answer("Введите ваше новое имя:", reply_markup=get_navigation_keyboard())
    await callback.answer()

@settings_router.message(ClientSettings.waiting_for_edit_name)
async def process_client_edit_name(message: types.Message, state: FSMContext):
    if message.text == "⬅️ Назад" or message.text == "🏠 В меню":
        await state.clear()
        await message.answer("Изменение имени отменено.", reply_markup=get_main_keyboard(is_admin=False))
        return

    new_name = message.text.strip()
    if len(new_name) < 2:
        await message.answer("Имя слишком короткое. Попробуйте еще раз.")
        return

    await FirestoreDB.update_user(message.from_user.id, {"full_name": new_name})
    await state.clear()
    await message.answer(f"✅ Имя успешно обновлено на: {hbold(new_name)}", reply_markup=get_main_keyboard(is_admin=False))

@settings_router.callback_query(F.data == "client_edit_tz")
async def client_edit_tz_start(callback: types.CallbackQuery, state: FSMContext):
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    offsets = ["UTC-3", "UTC+0", "UTC+2", "UTC+3", "UTC+4", "UTC+5", "UTC+6", "UTC+7", "UTC+8", "UTC+9"]
    for off in offsets:
        builder.button(text=off, callback_data=f"client_save_tz_{off}")
    builder.adjust(3)
    
    await callback.message.edit_text("Выберите ваш часовой пояс:", reply_markup=builder.as_markup())
    await callback.answer()

@settings_router.callback_query(F.data.startswith("client_save_tz_"))
async def process_client_edit_tz(callback: types.CallbackQuery, state: FSMContext):
    new_tz = callback.data.replace("client_save_tz_", "")
    await FirestoreDB.update_user(callback.from_user.id, {"timezone": new_tz})
    
    current_state = await state.get_state()
    if current_state == ClientSettings.waiting_for_edit_timezone:
        # We are in the "Personalized Delivery" flow
        await callback.message.edit_text(f"✅ Часовой пояс {hbold(new_tz)} сохранен.\n\nТеперь введите желаемое время для {hbold('Утреннего Импульса')} в формате ЧЧ:ММ (например, 08:00):")
        await state.set_state(ClientSettings.waiting_for_morning_time)
    else:
        # Normal profile edit
        await callback.message.edit_text(f"✅ Часовой пояс обновлен на: {hbold(new_tz)}")
        await state.clear()
        
    await callback.answer("Сохранено!")

@settings_router.callback_query(F.data == "edit_delivery_times")
async def client_edit_delivery_start(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(ClientSettings.waiting_for_edit_timezone)
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    # Prioritize popular offsets, include UTC+7 (Vietnam)
    offsets = ["UTC+2", "UTC+3", "UTC+4", "UTC+5", "UTC+7", "UTC+8", "UTC+9"]
    for off in offsets:
        builder.button(text=off, callback_data=f"client_save_tz_{off}")
    builder.adjust(3)
    
    await callback.message.answer(
        "⚙️ {hbold('Настройка персонального времени доставки')}\n\n"
        "Шаг 1: Выберите ваш часовой пояс:",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@settings_router.message(ClientSettings.waiting_for_morning_time)
async def process_client_morning_time(message: types.Message, state: FSMContext):
    time_str = message.text.strip()
    if not re.match(r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$", time_str):
        await message.answer("❌ Неверный формат. Введите время как ЧЧ:ММ (например, 08:30):")
        return

    await state.update_data(morning_time=time_str)
    await message.answer(f"✅ Утреннее время {hbold(time_str)} принято.\n\nШаг 3: Введите время для {hbold('Вечернего Отчета')} (например, 21:00):")
    await state.set_state(ClientSettings.waiting_for_evening_time)

@settings_router.message(ClientSettings.waiting_for_evening_time)
async def process_client_evening_time(message: types.Message, state: FSMContext):
    time_str = message.text.strip()
    if not re.match(r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$", time_str):
        await message.answer("❌ Неверный формат. Введите время как ЧЧ:ММ (например, 22:00):")
        return

    data = await state.get_data()
    morning_time = data.get('morning_time')
    
    await FirestoreDB.update_user(message.from_user.id, {
        "morning_time": morning_time,
        "evening_time": time_str
    })
    
    await state.clear()
    await message.answer(
        f"🎉 {hbold('Настройки успешно сохранены!')}\n\n"
        f"🌅 Утренний импульс: {hbold(morning_time)}\n"
        f"🌙 Вечерний отчет: {hbold(time_str)}\n\n"
        f"Система будет присылать задания и запросы по твоему местному времени.",
        reply_markup=get_main_keyboard(is_admin=False)
    )

# --- Global Admin Settings Handlers ---

@settings_router.callback_query(F.data.startswith("trigger_"))
async def trigger_manual_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    logger.info(f"🖱 [ADMIN] Button click: {callback.data} by user {user_id}")
    
    if not is_admin(user_id):
        logger.warning(f"🚫 [AUTH] Unauthorized attempt by {user_id}")
        await callback.answer("У вас нет прав администратора.", show_alert=True)
        return
        
    action = callback.data.replace("trigger_", "")
    logger.info(f"⚡ [ADMIN] Manually triggering action: {action}")
    
    from utils.scheduler import send_morning_impulse, request_evening_logs, send_group_weekly_report
    
    try:
        if action == "morning":
            await callback.message.answer("🚀 Запускаю рассылку утренних импульсов...")
            count = await send_morning_impulse(callback.bot)
            await callback.message.answer(f"✅ Рассылка импульсов завершена. Отправлено: {count} чел.")
        elif action == "evening":
            await callback.message.answer("📝 Запускаю сбор вечерних отчетов...")
            count = await request_evening_logs(callback.bot)
            await callback.message.answer(f"✅ Сбор отчетов запущен. Отправлено запросов: {count} чел.")
        elif action == "weekly":
            await callback.message.answer("📊 Запускаю рассылку итогов недели...")
            await send_group_weekly_report(callback.bot)
            await callback.message.answer("✅ Еженедельный отчет отправлен всем админам.")
        
        await callback.answer("Запущено!")
        logger.info(f"✅ [ADMIN] Action {action} completed successfully.")
    except Exception as e:
        logger.error(f"❌ [ADMIN] Error triggering {action}: {e}", exc_info=True)
        await callback.message.answer(f"❌ Ошибка при запуске {action}: {e}")
        await callback.answer("Ошибка!")

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
    
    if not re.match(r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$", new_time):
        await message.answer("❌ Неверный формат. Пожалуйста, введите время как ЧЧ:ММ (например, 09:00 или 21:15).")
        return
        
    data = await state.get_data()
    time_type = data['time_type']
    
    field_map = {
        "morning": "morning_time",
        "deadline": "deadline_time",
        "evening": "evening_time",
        "sunday": "sunday_time"
    }
    
    await FirestoreDB.update_global_settings({field_map[time_type]: new_time})
    
    await state.clear()
    await message.answer(f"✅ Время обновлено на {hbold(new_time)}.")
    
    from utils.scheduler import reload_admin_jobs
    await reload_admin_jobs(message.bot)
