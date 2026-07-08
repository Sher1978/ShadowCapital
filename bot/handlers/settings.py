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
    builder.button(text="🔄 Синхронизировать базу", callback_data="trigger_sync_db")
        
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
        f"🎭 {hbold('Привязанность:')} {user.get('attachment_type') or 'Не задан'}\n"
        f"🏆 {hbold('Архетип:')} {user.get('archetype') or 'Не задан'}\n"
        f"🧩 {hbold('Социотип:')} {user.get('sociotype') or 'Не задан'}\n\n"
        f"💎 {hbold('Спринт Качество (L1):')} {user.get('target_quality_l1') or 'Не задано'}\n"
        f"🎬 {hbold('Спринт Сценарий:')} {user.get('scenario_type') or 'Не задан'}\n\n"
        f"Ты можешь изменить свои анкетные данные, имя или часовой пояс. Спринты (качество/сценарий) активируются только куратором."
    )
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text="✏️ Изменить Имя", callback_data="client_edit_name")
    builder.button(text="🌍 Изменить Часовой Пояс", callback_data="client_edit_tz")
    builder.button(text="🎭 Изменить Привязанность", callback_data="client_edit_attachment")
    builder.button(text="🏆 Изменить Архетип", callback_data="client_edit_archetype")
    builder.button(text="🧩 Изменить Социотип", callback_data="client_edit_sociotype")
    builder.button(text="📝 Пройти тест заново", url="https://shershadow.web.app/sfitest")
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
    
    # ПРЕДВЕЩАТЕЛЬНЫЙ ОТВЕТ НА КОЛБЕК, ЧТОБЫ НЕ БЫЛО ТАЙМАУТА (Query is too old)
    try:
        await callback.answer("Запускаю процесс, это может занять время...")
    except Exception:
        pass
    
    from utils.scheduler import send_morning_impulse, request_evening_logs, send_group_weekly_report
    
    try:
        # Immediate answer to acknowledge the click
        await callback.answer("⏳ Запуск процесса...", show_alert=False)
        
        # Update message to show progress
        original_text = callback.message.text
        await callback.message.edit_text(f"{original_text}\n\n⌛ {hbold('Процесс запущен...')}")

        if action == "morning":
            count = await send_morning_impulse(callback.bot)
            await callback.message.edit_text(f"{original_text}\n\n✅ {hbold('Рассылка завершена!')}\nОтправлено: {count} чел.")
        elif action == "evening":
            count = await request_evening_logs(callback.bot)
            await callback.message.edit_text(f"{original_text}\n\n✅ {hbold('Сбор отчетов запущен!')}\nОтправлено запросов: {count} чел.")
        elif action == "weekly":
            await send_group_weekly_report(callback.bot)
            await callback.message.edit_text(f"{original_text}\n\n✅ {hbold('Еженедельный отчет отправлен!')}")
        elif action == "sync_db":
            from utils.gsheets_api import sync_gsheets_to_firestore
            count = await sync_gsheets_to_firestore()
            await callback.message.edit_text(f"{original_text}\n\n✅ {hbold('База синхронизирована!')}\nОбновлено {count} заданий.")
        
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


# --- Interactive Profile Field Editing (Attachment, Archetype, Sociotype) ---

@settings_router.callback_query(F.data == "client_edit_attachment")
async def client_edit_attachment_start(callback: types.CallbackQuery):
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    
    builder.button(text="Надежный", callback_data="save_client_attachment_Надежный")
    builder.button(text="Тревожный", callback_data="save_client_attachment_Тревожный")
    builder.button(text="Избегающий", callback_data="save_client_attachment_Избегающий")
    builder.button(text="Тревожно-избегающий", callback_data="save_client_attachment_Тревожно-избегающий")
    
    builder.row(types.InlineKeyboardButton(text="⬅️ Назад", callback_data="client_back_to_settings"))
    builder.adjust(1)
    
    await callback.message.edit_text("Выберите ваш тип привязанности:", reply_markup=builder.as_markup())
    await callback.answer()

@settings_router.callback_query(F.data.startswith("save_client_attachment_"))
async def save_client_attachment(callback: types.CallbackQuery):
    val = callback.data.replace("save_client_attachment_", "")
    user = await FirestoreDB.get_user(callback.from_user.id)
    if user:
        await FirestoreDB.update_user(user['id'], {"attachment_type": val})
        await callback.message.answer(f"✅ Тип привязанности обновлен на: {hbold(val)}")
    await callback.answer()
    # Go back to settings view
    await client_settings_handler(callback.message)
    await callback.message.delete()

@settings_router.callback_query(F.data == "client_edit_archetype")
async def client_edit_archetype_start(callback: types.CallbackQuery):
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    
    builder.button(text="Sovereign", callback_data="save_client_archetype_Sovereign")
    builder.button(text="Expansion", callback_data="save_client_archetype_Expansion")
    builder.button(text="Vitality", callback_data="save_client_archetype_Vitality")
    builder.button(text="Architect", callback_data="save_client_archetype_Architect")
    
    builder.row(types.InlineKeyboardButton(text="⬅️ Назад", callback_data="client_back_to_settings"))
    builder.adjust(1)
    
    await callback.message.edit_text("Выберите ваш ведущий архетип:", reply_markup=builder.as_markup())
    await callback.answer()

@settings_router.callback_query(F.data.startswith("save_client_archetype_"))
async def save_client_archetype(callback: types.CallbackQuery):
    val = callback.data.replace("save_client_archetype_", "")
    user = await FirestoreDB.get_user(callback.from_user.id)
    if user:
        await FirestoreDB.update_user(user['id'], {"archetype": val})
        await callback.message.answer(f"✅ Ведущий архетип обновлен на: {hbold(val)}")
    await callback.answer()
    await client_settings_handler(callback.message)
    await callback.message.delete()

@settings_router.callback_query(F.data == "client_edit_sociotype")
async def client_edit_sociotype_start(callback: types.CallbackQuery):
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    
    types_list = [
        ("ИЛЭ", "ИЛЭ (Дон Кихот)"), ("СЭИ", "СЭИ (Дюма)"), 
        ("ЭСО", "ЭСО (Гюго)"), ("ЛИИ", "ЛИИ (Робеспьер)"),
        ("ЭИЭ", "ЭИЭ (Гамлет)"), ("ЛСИ", "ЛСИ (Максим Горький)"), 
        ("СЛЭ", "СЛЭ (Жуков)"), ("ИЭИ", "ИЭИ (Есенин)"),
        ("СЭЭ", "СЭЭ (Наполеон)"), ("ИЛИ", "ИЛИ (Бальзак)"), 
        ("ЛИЭ", "ЛИЭ (Джек Лондон)"), ("ЭСИ", "ЭСИ (Драйзер)"),
        ("ЛСЭ", "ЛСЭ (Штирлиц)"), ("ЭИИ", "ЭИИ (Достоевский)"), 
        ("ИЭЭ", "ИЭЭ (Гексли)"), ("СЛИ", "СЛИ (Габен)")
    ]
    
    for code, full_name in types_list:
        builder.button(text=full_name, callback_data=f"save_client_socio_{code}")
        
    builder.row(types.InlineKeyboardButton(text="⬅️ Назад", callback_data="client_back_to_settings"))
    builder.adjust(2)
    
    await callback.message.edit_text("Выберите ваш социотип:", reply_markup=builder.as_markup())
    await callback.answer()

@settings_router.callback_query(F.data.startswith("save_client_socio_"))
async def save_client_sociotype(callback: types.CallbackQuery):
    code = callback.data.replace("save_client_socio_", "")
    types_map = {
        "ИЛЭ": "ИЛЭ (Дон Кихот)", "СЭИ": "СЭИ (Дюма)", 
        "ЭСО": "ЭСО (Гюго)", "ЛИИ": "ЛИИ (Робеспьер)",
        "ЭИЭ": "ЭИЭ (Гамлет)", "ЛСИ": "ЛСИ (Максим Горький)", 
        "СЛЭ": "СЛЭ (Жуков)", "ИЭИ": "ИЭИ (Есенин)",
        "СЭЭ": "СЭЭ (Наполеон)", "ИЛИ": "ИЛИ (Бальзак)", 
        "ЛИЭ": "ЛИЭ (Джек Лондон)", "ЭСИ": "ЭСИ (Драйзер)",
        "ЛСЭ": "ЛСЭ (Штирлиц)", "ЭИИ": "ЭИИ (Достоевский)", 
        "ИЭЭ": "ИЭЭ (Гексли)", "СЛИ": "СЛИ (Габен)"
    }
    val = types_map.get(code, code)
    user = await FirestoreDB.get_user(callback.from_user.id)
    if user:
        await FirestoreDB.update_user(user['id'], {"sociotype": val})
        await callback.message.answer(f"✅ Социотип обновлен на: {hbold(val)}")
    await callback.answer()
    await client_settings_handler(callback.message)
    await callback.message.delete()

@settings_router.callback_query(F.data == "client_back_to_settings")
async def client_back_to_settings_callback(callback: types.CallbackQuery):
    await callback.answer()
    await client_settings_handler(callback.message)
    await callback.message.delete()
