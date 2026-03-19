import logging
from datetime import datetime, timezone

from aiogram import Router, F, types, Bot
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.utils.markdown import hbold

from config import ADMIN_IDS
from database.firebase_db import FirestoreDB
from bot.states import AdminStates, AdminRegistration
from bot.keyboards.builders import get_main_keyboard
from utils.scheduler import send_morning_impulse, send_weekly_briefings, request_evening_logs
from utils.gsheets_api import sync_user_to_sheets

logger = logging.getLogger(__name__)
admin_router = Router()

def is_admin(user_id: int) -> bool:
    res = user_id in ADMIN_IDS
    logger.info(f"🛡 Admin Check for {user_id}: {res} (ADMIN_IDS: {ADMIN_IDS})")
    return res

@admin_router.message(F.text == "DEBUG_TEST", StateFilter("*"))
async def debug_test_handler(message: types.Message):
    await message.answer(f"✅ Router reached. Your ID: {message.from_user.id}")

@admin_router.message(Command("trigger_morning"))
async def trigger_morning_handler(message: types.Message, bot: Bot):
    if not is_admin(message.from_user.id):
        return
    
    args = message.text.split()
    target_user = None
    
    if len(args) > 1:
        target = args[1].strip().replace("@", "")
        if target.isdigit():
            target_user = await FirestoreDB.get_user(int(target))
        else:
            # Simple username search in Firestore (limited by indexed fields)
            docs = FirestoreDB.db.collection("users").where("username", "==", target).limit(1).stream()
            for doc in docs:
                target_user = doc.to_dict()
                target_user['id'] = doc.id
                break
            
        if not target_user:
            await message.answer(f"❌ Пользователь {target} не найден.")
            return
    
    if target_user:
        await message.answer(f"🚀 Запускаю утренний импульс для {target_user.get('full_name')}...")
        await send_morning_impulse(bot, target_user)
        await message.answer("✅ Отправлено.")
    else:
        # Mass trigger protection
        await message.answer("⚠️ Запускаю рассылку утренних импульсов для ВСЕХ активных клиентов...")
        await send_morning_impulse(bot)
        await message.answer("✅ Массовая рассылка завершена.")

@admin_router.message(Command("trigger_evening"))
async def trigger_evening_handler(message: types.Message, bot: Bot):
    if not is_admin(message.from_user.id):
        return
        
    args = message.text.split()
    target_user = None
    
    if len(args) > 1:
        target = args[1].strip().replace("@", "")
        if target.isdigit():
            target_user = await FirestoreDB.get_user(int(target))
        else:
            docs = FirestoreDB.db.collection("users").where("username", "==", target).limit(1).stream()
            for doc in docs:
                target_user = doc.to_dict()
                target_user['id'] = doc.id
                break
            
        if not target_user:
            await message.answer(f"❌ Пользователь {target} не найден.")
            return

    if target_user:
        await message.answer(f"🌙 Запрашиваю вечерний лог у {target_user.get('full_name')}...")
        await request_evening_logs(bot, target_user)
        await message.answer("✅ Запрос отправлен.")
    else:
        await message.answer("⚠️ Запрашиваю вечерние логи у ВСЕХ активных клиентов...")
        await request_evening_logs(bot)
        await message.answer("✅ Все запросы отправлены.")

@admin_router.message(Command("trigger_weekly"))
async def trigger_weekly_handler(message: types.Message, bot: Bot):
    if not is_admin(message.from_user.id):
        return
    await message.answer("Запускаю генерацию сводного отчета по группе...")
    from utils.scheduler import send_group_weekly_report
    await send_group_weekly_report(bot)
    await message.answer("Сводный отчет сгенерирован и отправлен.")

# --- Sprint 8: Direct Reply ---

@admin_router.callback_query(F.data.startswith("ai_reply_"))
async def admin_reply_start(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    client_id = callback.data.split("_")[-1]
    await state.update_data(reply_to_client_id=client_id)
    await state.set_state(AdminStates.waiting_for_reply_text)
    await callback.message.answer(f"Введите сообщение для клиента {client_id} (или /cancel для отмены):")
    await callback.answer()

@admin_router.message(AdminStates.waiting_for_reply_text)
async def admin_reply_handler(message: types.Message, state: FSMContext, bot: Bot):
    if not is_admin(message.from_user.id):
        return
    
    data = await state.get_data()
    client_id = data.get("reply_to_client_id")
    
    if not client_id:
        await message.answer("Ошибка: ID клиента не найден.")
        await state.clear()
        return

    try:
        reply_text = f"✉️ {hbold('Сообщение от куратора:')}\n\n{message.text}"
        await bot.send_message(client_id, reply_text)
        await message.answer(f"Сообщение отправлено клиенту {client_id}.")
    except Exception as e:
        await message.answer(f"Ошибка при отправке: {e}")
    
    await state.clear()

@admin_router.message(F.text == "💼 Админ Панель")
async def admin_panel_handler(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    
    text = (
        f"{hbold('Доступные команды:')}\n\n"
        "/add_client - Добавить клиента (30 дней)\n"
        "/trigger_morning - Запуск утренних импульсов\n"
        "/trigger_evening - Запрос вечерних логов\n"
        "/trigger_weekly - Сбор еженедельных сводок\n"
    )
    await message.answer(text)

@admin_router.message(F.text.contains("Заявки"), StateFilter("*"))
async def pending_list_handler(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    logger.info(f"🖱 [ENTRY] pending_list_handler hit by {user_id}. Text: '{message.text}'")
    
    if not is_admin(user_id):
        logger.warning(f"🚫 Unauthorized attempt to access 'Requests' by user {user_id}")
        return
        
    # Extra safety: Clear state if it wasn't cleared by middleware
    cur_state = await state.get_state()
    if cur_state:
        logger.info(f"🔄 Safety FSM Clear in handler for user {user_id} (State: {cur_state})")
        await state.clear()
        
    await show_pending_page(message)

async def show_pending_page(message: types.Message, page: int = 0):
    limit = 10
    offset = page * limit
    
    # Firestore doesn't support offset naturally, we'd use start_at for proper pagination.
    # For now, simple limit stream is fine for "pending" list.
    logger.debug(f"🔍 [QUERY] Starting Firestore query for status=pending (limit {limit})")
    docs = FirestoreDB.db.collection("users").where("status", "==", "pending").limit(limit).stream()
    users = []
    logger.debug("🔍 [QUERY] Iterating results...")
    for doc in docs:
        d = doc.to_dict()
        d['id'] = doc.id
        users.append(d)
    logger.info(f"🔍 [QUERY] Found {len(users)} pending users.")
        
    if not users and page == 0:
        if isinstance(message, types.CallbackQuery):
            await message.message.edit_text("Список заявок пуст.")
        else:
            await message.answer("Список заявок пуст.")
        return

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    
    for u in users:
        name = u.get('full_name') or f"ID: {u.get('tg_id')}"
        username = f" (@{u.get('username')})" if u.get('username') else ""
        builder.button(text=f"👤 {name}{username}", callback_data=f"view_pending_{u.get('tg_id')}")
        
    builder.adjust(1)
    
    # Pagination buttons (Simplified for now)
    nav_buttons = []
    if page > 0:
        nav_buttons.append(types.InlineKeyboardButton(text="⬅️ Назад", callback_data=f"pending_page_{page-1}"))
    if len(users) == limit:
        nav_buttons.append(types.InlineKeyboardButton(text="Вперед ➡️", callback_data=f"pending_page_{page+1}"))
    
    if nav_buttons:
        builder.row(*nav_buttons)
            
    text = f"⏳ {hbold('Список заявок на активацию')} (Стр. {page + 1}):"
    if isinstance(message, types.CallbackQuery):
        await message.message.edit_text(text, reply_markup=builder.as_markup())
    else:
        await message.answer(text, reply_markup=builder.as_markup())

@admin_router.callback_query(F.data.startswith("pending_page_"))
async def process_pending_pagination(callback: types.CallbackQuery):
    page = int(callback.data.split("_")[-1])
    await show_pending_page(callback, page)
    await callback.answer()

@admin_router.message(F.text.contains("Клиенты") | F.text.contains("Спринты"), StateFilter("*"))
async def active_sprints_handler(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    logger.info(f"🖱 [ENTRY] active_sprints_handler hit by {user_id}. Text: '{message.text}'")
    
    if not is_admin(user_id):
        logger.warning(f"🚫 Unauthorized attempt to access 'Clients' by user {user_id}")
        return
        
    # Extra safety: Clear state if it wasn't cleared by middleware
    cur_state = await state.get_state()
    if cur_state:
        logger.info(f"🔄 Safety FSM Clear in handler for user {user_id} (State: {cur_state})")
        await state.clear()
        
    await show_active_page(message)

async def show_active_page(message: types.Message, page: int = 0):
    limit = 10
    offset = page * limit
    
    logger.debug(f"🔍 [QUERY] Starting Firestore query for status=active (limit {limit})")
    docs = FirestoreDB.db.collection("users").where("status", "==", "active").limit(limit).stream()
    users = []
    logger.debug("🔍 [QUERY] Iterating results...")
    for doc in docs:
        d = doc.to_dict()
        d['id'] = doc.id
        users.append(d)
        
    if not users and page == 0:
        if isinstance(message, types.CallbackQuery):
            await message.message.edit_text("Активных спринтов пока нет.")
        else:
            await message.answer("Активных спринтов пока нет.")
        return

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    
    for u in users:
        name = u.get('full_name') or f"ID: {u.get('tg_id')}"
        sfi = f"SFI: {round(u.get('sfi_index', 1.0), 2)}"
        builder.button(text=f"🚀 {name} ({sfi})", callback_data=f"view_stats_{u.get('tg_id')}")
        
    builder.adjust(1)
    
    nav_buttons = []
    if page > 0:
        nav_buttons.append(types.InlineKeyboardButton(text="⬅️ Назад", callback_data=f"active_page_{page-1}"))
    if len(users) == limit:
        nav_buttons.append(types.InlineKeyboardButton(text="Вперед ➡️", callback_data=f"active_page_{page+1}"))
    
    if nav_buttons:
        builder.row(*nav_buttons)
            
    text = f"🚀 {hbold('Активные Спринты')} (Стр. {page + 1}):"
    if isinstance(message, types.CallbackQuery):
        await message.message.edit_text(text, reply_markup=builder.as_markup())
    else:
        await message.answer(text, reply_markup=builder.as_markup())

@admin_router.message(F.text.contains("Аналитика"), StateFilter("*"))
async def admin_analytics_handler(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    # Safety clear
    await state.clear()
    
    # Get counts using Firestore aggregation
    total_users_query = FirestoreDB.db.collection("users").count()
    active_users_query = FirestoreDB.db.collection("users").where("status", "==", "active").count()
    pending_users_query = FirestoreDB.db.collection("users").where("status", "==", "pending").count()
    
    total_users = total_users_query.get()[0][0].value
    active_users = active_users_query.get()[0][0].value
    pending_users = pending_users_query.get()[0][0].value
    
    # Simple average calculation (async)
    active_docs = FirestoreDB.db.collection("users").where("status", "==", "active").stream()
    sfi_values = [doc.to_dict().get('sfi_index', 1.0) for doc in active_docs]
    avg_sfi = sum(sfi_values) / len(sfi_values) if sfi_values else 1.0
    
    text = (
        f"📊 {hbold('Аналитика группы:')}\n\n"
        f"👥 Всего пользователей: {total_users}\n"
        f"🚀 Активных спринтов: {active_users}\n"
        f"⏳ В очереди (Pending): {pending_users}\n\n"
        f"📈 Средний SFI группы: {round(float(avg_sfi), 2)}\n\n"
        f"💡 Для детальной статистики выберите клиента в списке '👥 Клиенты'."
    )
    await message.answer(text)

@admin_router.callback_query(F.data.startswith("active_page_"))
async def process_active_pagination(callback: types.CallbackQuery):
    page = int(callback.data.split("_")[-1])
    await show_active_page(callback, page)
    await callback.answer()

@admin_router.callback_query(F.data.startswith("view_stats_"))
async def view_user_stats_handler(callback: types.CallbackQuery):
    tg_id = int(callback.data.split("_")[-1])
    user = await FirestoreDB.get_user(tg_id)
    
    if not user:
        await callback.answer("Пользователь не найден.")
        return
        
    # Calculate Sprint Day
    sprint_day = "N/A"
    start_date = user.get('sprint_start_date')
    if start_date:
        if isinstance(start_date, str):
             start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        delta = datetime.now(timezone.utc) - start_date
        sprint_day = delta.days + 1

    # Friction Level Logic (SFI: 0.1 goal, 1.0 critical)
    friction = "🟢 GREEN"
    sfi = user.get('sfi_index', 1.0)
    flags = user.get('red_flags_count', 0)
    
    if sfi > 0.7 or flags >= 3:
        friction = "🔴 RED"
    elif sfi > 0.4 or flags >= 2:
        friction = "🟡 YELLOW"

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text="✉️ Написать клиенту", callback_data=f"ai_reply_{tg_id}")
    builder.button(text="☀️ Утренний Импульс", callback_data=f"test_morning_{tg_id}")
    builder.button(text="🌙 Вечерний Лог", callback_data=f"test_evening_{tg_id}")
    builder.button(text="⚙️ Редактировать профиль", callback_data=f"edit_profile_{tg_id}")
    builder.button(text="⬅️ К списку", callback_data="active_page_0")
    builder.adjust(1, 2, 1, 1)
    
    text = (
        f"📊 {hbold('Статистика Спринта:')}\n\n"
        f"👤 Имя: {user.get('full_name')}\n"
        f"📅 День Спринта: {sprint_day}/30\n"
        f"🎯 Качество (L1): {user.get('target_quality_l1')}\n"
        f"👁 Сценарий: {user.get('scenario_type')}\n\n"
        f"📈 Shadow Friction Index (SFI): {round(sfi, 2)}\n"
        f"🚩 Флаги саботажа: {flags}\n"
        f"🌡 Уровень трения: {friction}\n\n"
        f"💡 {hbold('Последний инсайт:')}\n"
        f"{user.get('last_insight') or 'Данных пока нет.'}"
    )
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@admin_router.callback_query(F.data.startswith("view_pending_"))
async def view_pending_user_handler(callback: types.CallbackQuery):
    tg_id = int(callback.data.split("_")[-1])
    user = await FirestoreDB.get_user(tg_id)
    if not user:
        await callback.answer("Пользователь не найден.")
        return
        
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Запустить обучение", callback_data=f"approve_user_{tg_id}")
    builder.button(text="❌ Отклонить", callback_data=f"reject_user_{tg_id}")
    builder.button(text="⬅️ К списку", callback_data="pending_page_0")
    builder.adjust(2, 1)
    
    text = (
        f"👤 {hbold('Данные заявителя:')}\n\n"
        f"Имя: {user.get('full_name')}\n"
        f"Username: @{user.get('username') or 'N/A'}\n"
        f"TG ID: {user.get('tg_id')}\n\n"
        f"Выбери действие:"
    )
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@admin_router.callback_query(F.data.startswith("test_morning_"))
async def admin_test_morning_handler(callback: types.CallbackQuery, bot: Bot):
    tg_id = int(callback.data.split("_")[-1])
    user = await FirestoreDB.get_user(tg_id)
    if user:
        await send_morning_impulse(bot, user)
        await callback.answer("✅ Утренний импульс отправлен!")
    else:
        await callback.answer("❌ Ошибка: клиент не найден.")

@admin_router.callback_query(F.data.startswith("reject_user_"))
async def reject_user_handler(callback: types.CallbackQuery, bot: Bot):
    tg_id = int(callback.data.split("_")[-1])
    user = await FirestoreDB.get_user(tg_id)
    if user:
        await FirestoreDB.update_user(user['id'], {"status": "rejected"})
        try:
            await bot.send_message(tg_id, "❌ К сожалению, твоя заявка на активацию Спринта была отклонена.")
        except: pass
            
    await callback.message.edit_text("❌ Заявка отклонена.")
    await callback.answer()

@admin_router.callback_query(F.data.startswith("approve_user_"))
async def approve_user_start_registration(callback: types.CallbackQuery, state: FSMContext):
    tg_id = int(callback.data.split("_")[-1])
    await state.update_data(tg_id=tg_id)
    
    user = await FirestoreDB.get_user(tg_id)
    if user:
        await state.update_data(full_name=user.get('full_name'))
    
    await state.set_state(AdminRegistration.waiting_for_quality_name)
    await callback.message.answer(f"Начинаем регистрацию для ID {tg_id}.\nВведите название Теневого Качества (L1):")
    await callback.answer()

@admin_router.message(F.text.contains("Добавить клиента"), StateFilter("*"))
@admin_router.message(Command("add_client"), StateFilter("*"))
async def start_add_client(message: types.Message, state: FSMContext):
    logger.info(f"🖱 Button 'Add Client' clicked by {message.from_user.id}")
    if not is_admin(message.from_user.id):
        return
    
    await state.clear() # Clear any previous state before starting new registration
    
    await state.set_state(AdminRegistration.waiting_for_username)
    await message.answer("Введите Telegram Ник (@username) нового клиента для активации:")

# THIS MUST BE THE LAST HANDLER IN THE ROUTER FOR DEBUGGING
@admin_router.message(StateFilter("*"))
async def admin_catch_all(message: types.Message):
    logger.info(f"📝 [CATCH-ALL] Admin router received: '{message.text}' from {message.from_user.id}")

@admin_router.message(AdminRegistration.waiting_for_username)
async def process_username(message: types.Message, state: FSMContext):
    username = message.text.strip().replace("@", "")
    
    # Query by username in Firestore
    docs = FirestoreDB.db.collection("users").where("username", "==", username).limit(1).stream()
    user = None
    for doc in docs:
        user = doc.to_dict()
        user['id'] = doc.id
        break
        
    if not user:
        await message.answer(
            f"❌ Пользователь с ником @{username} не найден в базе бота.\n\n"
            f"Клиент должен сначала запустить бота (/start), чтобы мы могли его активировать. "
            f"Попробуйте другой ник или попросите его нажать /start."
        )
        return
    
    await state.update_data(tg_id=user.get('tg_id'))
    await state.set_state(AdminRegistration.waiting_for_full_name)
    
    from aiogram.utils.keyboard import ReplyKeyboardBuilder
    builder = ReplyKeyboardBuilder()
    builder.button(text=user.get('full_name') or "Без имени")
    builder.adjust(1)
    
    await message.answer(
        f"✅ Пользователь найден: {user.get('full_name')} (ID: {user.get('tg_id')})\n"
        f"Введите Имя для Спринта (или выберите предложенное):",
        reply_markup=builder.as_markup(resize_keyboard=True)
    )

@admin_router.message(AdminRegistration.waiting_for_full_name)
async def process_full_name(message: types.Message, state: FSMContext):
    await state.update_data(full_name=message.text)
    await state.set_state(AdminRegistration.waiting_for_quality_name)
    await message.answer("Введите название Теневого Качества (L1):")

@admin_router.message(AdminRegistration.waiting_for_quality_name)
async def process_quality_name(message: types.Message, state: FSMContext):
    await state.update_data(quality_name=message.text)
    await state.set_state(AdminRegistration.waiting_for_scenario_type)
    text = (
        f"Выберите тип сценария:\n\n"
        f"1. {hbold('Sovereign')}\n"
        f"2. {hbold('Expansion')}\n"
        f"3. {hbold('Vitality')}\n"
        f"4. {hbold('Architect')}\n\n"
        f"Введите цифру (1-4):"
    )
    await message.answer(text)

@admin_router.message(AdminRegistration.waiting_for_scenario_type)
async def process_scenario_type(message: types.Message, state: FSMContext, bot: Bot):
    scenario_map = {
        "1": "Sovereign",
        "2": "Expansion",
        "3": "Vitality",
        "4": "Architect"
    }
    
    choice = message.text.strip()
    if choice in scenario_map:
        scenario_type = scenario_map[choice]
    else:
        # Fallback to direct text if not a number
        scenario_type = choice
        
    await state.update_data(scenario_type=scenario_type)
    
    descriptions = {
        "Sovereign": "Возврат личной власти, радикальная ответственность и «вступление на трон» бизнеса.",
        "Expansion": "Снятие внутренних границ, мешающих росту. Работа с «Большой Игрой» и захват новых территорий.",
        "Vitality": "Интеграция Тени для прекращения «слива» энергии в маски. Фокус на эффективности и драйве.",
        "Architect": "Структурирование хаоса Тени в твердую бизнес-архитектуру. Система на Zero Friction."
    }
    
    desc = descriptions.get(scenario_type, "Описание отсутствует.")
    
    from aiogram.utils.keyboard import ReplyKeyboardBuilder
    builder = ReplyKeyboardBuilder()
    builder.button(text="✅ Принять")
    builder.button(text="❌ Отмена")
    builder.adjust(2)
    
    text = (
        f"Выбран сценарий: {hbold(scenario_type)}\n\n"
        f"💡 {hbold('Юз-кейс:')}\n{desc}\n\n"
        f"Активируем клиента?"
    )
    await state.set_state(AdminRegistration.waiting_for_confirmation)
    await message.answer(text, reply_markup=builder.as_markup(resize_keyboard=True))

@admin_router.message(AdminRegistration.waiting_for_confirmation)
async def process_activation_confirmation(message: types.Message, state: FSMContext, bot: Bot):
    if message.text == "❌ Отмена":
        await state.set_state(AdminRegistration.waiting_for_scenario_type)
        text = (
            f"Выберите тип сценария:\n\n"
            f"1. {hbold('Sovereign')}\n"
            f"2. {hbold('Expansion')}\n"
            f"3. {hbold('Vitality')}\n"
            f"4. {hbold('Architect')}\n\n"
            f"Введите цифру (1-4):"
        )
        await message.answer(text, reply_markup=types.ReplyKeyboardRemove())
        return

    if message.text != "✅ Принять":
        await message.answer("Пожалуйста, используйте кнопки: ✅ Принять или ❌ Отмена")
        return

    data = await state.get_data()
    scenario_type = data['scenario_type']
    
    user = await FirestoreDB.get_user(data['tg_id'])
    
    user_payload = {
        "tg_id": data['tg_id'],
        "full_name": data['full_name'],
        "role": "client",
        "scenario_type": scenario_type,
        "target_quality_l1": data['quality_name'],
        "status": "active",
        "sfi_index": 1.0,
        "sprint_start_date": datetime.now(timezone.utc)
    }
    
    if not user:
        await FirestoreDB.create_user(user_payload)
    else:
        await FirestoreDB.update_user(user['id'], user_payload)
    
    # Sync to Google Sheets
    await sync_user_to_sheets({
        "user_id": data['tg_id'],
        "name": data['full_name'],
        "target_quality": data['quality_name'],
        "scenario": scenario_type,
        "red_flags": 0
    })
    
    await state.clear()
    await message.answer(
        f"✅ Клиент {data['tg_id']} успешно активирован!\nСценарий: {hbold(scenario_type)}",
        reply_markup=get_main_keyboard(is_admin=True)
    )
    
    # Notify client
    try:
        welcome_text = (
            f"Привет! Твой Shadow Sprint активирован.\n"
            f"Твоя цель на ближайшие 30 дней — интеграция качества {hbold(data['quality_name'])}.\n"
            f"Хранитель будет сопротивляться, но я здесь, чтобы мы прошли этот путь незаметно для него."
        )
        await bot.send_message(data['tg_id'], welcome_text, reply_markup=get_main_keyboard())
    except Exception as e:
        await message.answer(f"Не удалось отправить уведомление клиенту напрямую: {e}")

# --- Sprint 31: Client Profile Management ---

@admin_router.callback_query(F.data.startswith("edit_profile_"))
async def edit_profile_start(callback: types.CallbackQuery, state: FSMContext):
    client_id = int(callback.data.split("_")[-1])
    await state.update_data(edit_client_id=client_id)
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text="🎯 Качество (L1)", callback_data="edit_field_quality")
    builder.button(text="👁 Сценарий", callback_data="edit_field_scenario")
    builder.button(text="⬅️ Отмена", callback_data=f"view_stats_{client_id}")
    builder.adjust(1)
    
    await callback.message.edit_text("Что именно нужно изменить?", reply_markup=builder.as_markup())
    await callback.answer()

@admin_router.callback_query(F.data == "edit_field_quality")
async def edit_quality_start(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.waiting_for_edit_quality)
    await callback.message.answer("Введите новое название Теневого Качества (L1) или /cancel:")
    await callback.answer()

@admin_router.message(AdminStates.waiting_for_edit_quality)
async def process_edit_quality(message: types.Message, state: FSMContext):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("Редактирование отменено.", reply_markup=get_main_keyboard(is_admin=True))
        return
        
    data = await state.get_data()
    client_id = data.get("edit_client_id")
    new_quality = message.text.strip()
    
    user = await FirestoreDB.get_user(client_id)
    if user:
        await FirestoreDB.update_user(user['id'], {"target_quality_l1": new_quality})
        
        # Sync to Sheets
        await sync_user_to_sheets({
            "user_id": user.get('tg_id'),
            "name": user.get('full_name'),
            "target_quality": new_quality,
            "scenario": user.get('scenario_type'),
            "red_flags": user.get('red_flags_count') or 0,
            "sfi_index": user.get('sfi_index') or 1.0
        })
        await message.answer(f"✅ Качество обновлено на: {hbold(new_quality)}", reply_markup=get_main_keyboard(is_admin=True))
    else:
        await message.answer("Ошибка: клиент не найден.")
    
    await state.clear()

@admin_router.callback_query(F.data == "edit_field_scenario")
async def edit_scenario_start(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.waiting_for_edit_scenario)
    text = (
        f"Выберите новый тип сценария:\n\n"
        f"1. {hbold('Sovereign')}\n"
        f"2. {hbold('Expansion')}\n"
        f"3. {hbold('Vitality')}\n"
        f"4. {hbold('Architect')}\n\n"
        f"Введите цифру (1-4) или /cancel:"
    )
    await callback.message.answer(text)
    await callback.answer()

@admin_router.message(AdminStates.waiting_for_edit_scenario)
async def process_edit_scenario(message: types.Message, state: FSMContext):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("Редактирование отменено.", reply_markup=get_main_keyboard(is_admin=True))
        return

    scenario_map = {
        "1": "Sovereign",
        "2": "Expansion",
        "3": "Vitality",
        "4": "Architect"
    }
    
    choice = message.text.strip()
    if choice in scenario_map:
        scenario_type = scenario_map[choice]
    else:
        scenario_type = choice
        
    await state.update_data(edit_scenario_type=scenario_type)
    
    descriptions = {
        "Sovereign": "Возврат личной власти, радикальная ответственность и «вступление на трон» бизнеса.",
        "Expansion": "Снятие внутренних границ, мешающих росту. Работа с «Большой Игрой» и захват новых территорий.",
        "Vitality": "Интеграция Тени для прекращения «слива» энергии в маски. Фокус на эффективности и драйве.",
        "Architect": "Структурирование хаоса Тени в твердую бизнес-архитектуру. Система на Zero Friction."
    }
    
    desc = descriptions.get(scenario_type, "Описание отсутствует.")
    
    from aiogram.utils.keyboard import ReplyKeyboardBuilder
    builder = ReplyKeyboardBuilder()
    builder.button(text="✅ Подтвердить изменение")
    builder.button(text="❌ Отмена")
    builder.adjust(2)
    
    text = (
        f"Выбран новый сценарий: {hbold(scenario_type)}\n\n"
        f"💡 {hbold('Юз-кейс:')}\n{desc}\n\n"
        f"Сменить сценарий для клиента?"
    )
    await state.set_state(AdminStates.waiting_for_edit_scenario_confirm)
    await message.answer(text, reply_markup=builder.as_markup(resize_keyboard=True))

@admin_router.message(AdminStates.waiting_for_edit_scenario_confirm)
async def process_edit_scenario_confirmation(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Редактирование отменено.", reply_markup=get_main_keyboard(is_admin=True))
        return

    if message.text != "✅ Подтвердить изменение":
        await message.answer("Пожалуйста, используйте кнопки.")
        return

    data = await state.get_data()
    client_id = data.get("edit_client_id")
    new_scenario = data.get("edit_scenario_type")
    
    user = await FirestoreDB.get_user(client_id)
    if user:
        await FirestoreDB.update_user(user['id'], {"scenario_type": new_scenario})
        
        # Sync to Sheets
        await sync_user_to_sheets({
            "user_id": user.get('tg_id'),
            "name": user.get('full_name'),
            "target_quality": user.get('target_quality_l1'),
            "scenario": new_scenario,
            "red_flags": user.get('red_flags_count') or 0,
            "sfi_index": user.get('sfi_index') or 1.0
        })
        
        await message.answer(f"✅ Сценарий изменен на: {hbold(new_scenario)}", reply_markup=get_main_keyboard(is_admin=True))
    else:
        await message.answer("Ошибка: клиент не найден.")
            
    await state.clear()
