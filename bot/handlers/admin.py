import logging
from datetime import datetime, timezone, timedelta

from aiogram import Router, F, types, Bot
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.utils.markdown import hbold

from config import ADMIN_IDS, is_admin
from database.firebase_db import FirestoreDB
from bot.states import AdminStates, AdminRegistration
from bot.keyboards.builders import get_main_keyboard, get_navigation_keyboard, get_inline_back_button
from utils.scheduler import send_morning_impulse, send_weekly_briefings, request_evening_logs
from utils.gsheets_api import sync_user_to_sheets

logger = logging.getLogger(__name__)
admin_router = Router()


@admin_router.message(Command("trigger_morning"))
async def trigger_morning_handler(message: types.Message, bot: Bot):
    if not is_admin(message.from_user.id):
        await message.answer("⚠️ У тебя нет прав администратора.")
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
        await message.answer("⚠️ У тебя нет прав администратора.")
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
        await message.answer(f"🌙 Запрашиваю вечерний отчет у {target_user.get('full_name')}...")
        await request_evening_logs(bot, target_user)
        await message.answer("✅ Запрос отправлен.")
    else:
        await message.answer("⚠️ Запрашиваю вечерние отчеты у ВСЕХ активных клиентов...")
        await request_evening_logs(bot)
        await message.answer("✅ Все запросы отправлены.")

@admin_router.message(Command("trigger_weekly"))
async def trigger_weekly_handler(message: types.Message, bot: Bot):
    if not is_admin(message.from_user.id):
        await message.answer("⚠️ У тебя нет прав администратора.")
        return
    await message.answer("Запускаю генерацию сводного отчета по группе...")
    from utils.scheduler import send_group_weekly_report
    await send_group_weekly_report(bot)
    await message.answer("Сводный отчет сгенерирован и отправлен.")

# --- Navigation Handlers ---

@admin_router.message(F.text == "🏠 В меню", F.from_user.id.func(is_admin), StateFilter("*"))
async def back_to_menu_handler(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Возвращаемся в главное меню.", reply_markup=get_main_keyboard(is_admin=True))

@admin_router.message(F.text == "⬅️ Назад", AdminRegistration.waiting_for_full_name)
async def add_client_back_to_username(message: types.Message, state: FSMContext):
    await state.set_state(AdminRegistration.waiting_for_username)
    await message.answer("Введите Telegram Ник (@username) нового клиента для активации:", reply_markup=get_navigation_keyboard())

@admin_router.message(F.text == "⬅️ Назад", AdminRegistration.waiting_for_quality_name)
async def add_client_back_to_full_name(message: types.Message, state: FSMContext):
    data = await state.get_data()
    # Check if we came from username search or approve flow
    if data.get('tg_id') and not data.get('full_name'):
         await state.set_state(AdminRegistration.waiting_for_username)
         await message.answer("Введите Telegram Ник (@username) нового клиента для активации:", reply_markup=get_navigation_keyboard())
         return

    await state.set_state(AdminRegistration.waiting_for_full_name)
    await message.answer("Введите Имя для Спринта:", reply_markup=get_navigation_keyboard())

@admin_router.message(F.text == "⬅️ Назад", AdminRegistration.waiting_for_scenario_type)
async def add_client_back_to_quality(message: types.Message, state: FSMContext):
    await state.set_state(AdminRegistration.waiting_for_quality_name)
    await message.answer("Введите название Теневого Качества (L1):", reply_markup=get_navigation_keyboard())

@admin_router.message(F.text == "⬅️ Назад", AdminRegistration.waiting_for_timezone)
async def add_client_back_to_scenario(message: types.Message, state: FSMContext):
    await state.set_state(AdminRegistration.waiting_for_scenario_type)
    text = (
        f"Выберите тип сценария:\n\n"
        f"1. {hbold('Sovereign')}\n"
        f"2. {hbold('Expansion')}\n"
        f"3. {hbold('Vitality')}\n"
        f"4. {hbold('Architect')}\n\n"
        f"Введите цифру (1-4):"
    )
    await message.answer(text, reply_markup=get_navigation_keyboard())

@admin_router.message(F.text == "⬅️ Назад", AdminStates.waiting_for_reply_text)
async def edit_back_to_stats(message: types.Message, state: FSMContext):
    data = await state.get_data()
    client_id = data.get("reply_to_client_id") or data.get("edit_client_id")
    await state.clear()
    if client_id:
        # We need to re-show stats. Let's redirect to the callback handler logic
        # For simplicity, we just tell them to use the client list or we can re-query
        user = await FirestoreDB.get_user(client_id)
        if user:
             # We could call view_user_stats_handler, but it needs a CallbackQuery.
             # Better to just send the stats message.
             await message.answer("Возврат к статистике...", reply_markup=get_main_keyboard(is_admin=True))
             # Actually, the user wants the "Stats" message back.
             # I'll implement a helper for showing stats to reuse it.
             pass
    else:
        await message.answer("Возвращаемся в меню.", reply_markup=get_main_keyboard(is_admin=True))

@admin_router.message(F.text == "⬅️ Назад", AdminStates.waiting_for_edit_quality)
@admin_router.message(F.text == "⬅️ Назад", AdminStates.waiting_for_edit_scenario)
@admin_router.message(F.text == "⬅️ Назад", AdminStates.waiting_for_edit_day)
async def edit_field_back_to_profile(message: types.Message, state: FSMContext):
    data = await state.get_data()
    client_id = data.get("edit_client_id")
    # Instead of state clear, we just go back to edit selection
    # But edit_profile_start is a callback handler. 
    # Let's just go back to main menu or re-send edit menu.
    await message.answer("Редактирование отменено. Возврат в меню.", reply_markup=get_main_keyboard(is_admin=True))
    await state.clear()

# --- Sprint 8: Direct Reply ---

@admin_router.callback_query(F.data.startswith("ai_reply_"))
async def admin_reply_start(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⚠️ У тебя нет прав администратора.", show_alert=True)
        return
    client_id = callback.data.split("_")[-1]
    await state.update_data(reply_to_client_id=client_id)
    await state.set_state(AdminStates.waiting_for_reply_text)
    await callback.message.answer(
        f"Введите сообщение для клиента {client_id}:",
        reply_markup=get_navigation_keyboard()
    )
    await callback.answer()

@admin_router.message(AdminStates.waiting_for_reply_text)
async def admin_reply_handler(message: types.Message, state: FSMContext, bot: Bot):
    if not is_admin(message.from_user.id):
        await message.answer("⚠️ У тебя нет прав администратора.")
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

@admin_router.message(F.text == "💼 Админ Панель", F.from_user.id.func(is_admin))
async def admin_panel_handler(message: types.Message):
    
    text = (
        f"{hbold('Доступные команды:')}\n\n"
        "/add_client - Добавить клиента (30 дней)\n"
        "/trigger_morning - Запуск утренних импульсов\n"
        "/trigger_evening - Запрос вечерних логов\n"
        "/trigger_weekly - Сбор еженедельных сводок\n"
    )
    await message.answer(text)

@admin_router.message(F.text.contains("Заявки"), F.from_user.id.func(is_admin), StateFilter("*"))
async def pending_list_handler(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    logger.info(f" Handling 'Requests' list for {user_id}")
    
    logger.info(f"🔍 [ADMIN] 'Pending Requests' handler triggered by {user_id}")
        
    # Extra safety: Clear state if it wasn't cleared by middleware
    cur_state = await state.get_state()
    if cur_state:
        logger.info(f"🔄 FSM State cleared for Admin menu (User: {user_id})")
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
        if d.get('tg_id') in ADMIN_IDS:
            continue
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
    logger.info(f"✅ Pending list page {page} sent.")

@admin_router.callback_query(F.data.startswith("pending_page_"))
async def process_pending_pagination(callback: types.CallbackQuery):
    page = int(callback.data.split("_")[-1])
    await show_pending_page(callback, page)
    await callback.answer()

@admin_router.message(F.text.contains("Клиенты") | F.text.contains("Спринты") | (F.text == "📁 Архив"), F.from_user.id.func(is_admin), StateFilter("*"))
async def admin_clients_handler(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    logger.info(f"🔍 [ADMIN] Clients/Archive handler triggered by {user_id}")
    
    # Safety clear
    await state.clear()
    
    if message.text == "📁 Архив":
        await show_archived_page(message)
    else:
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
        if d.get('tg_id') in ADMIN_IDS:
            continue
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

async def show_archived_page(message: types.Message, page: int = 0):
    limit = 10
    offset = page * limit
    
    # Using the new method from firebase_db.py
    users = await FirestoreDB.get_archived_users(limit=limit, offset=offset)
        
    if not users and page == 0:
        msg_text = "Архив пуст."
        if isinstance(message, types.CallbackQuery):
            await message.message.edit_text(msg_text)
        else:
            await message.answer(msg_text)
        return

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    
    for u in users:
        name = u.get('full_name') or f"ID: {u.get('tg_id')}"
        builder.button(text=f"📁 {name}", callback_data=f"view_archived_{u.get('tg_id')}")
        
    builder.adjust(1)
    
    nav_buttons = []
    if page > 0:
        nav_buttons.append(types.InlineKeyboardButton(text="⬅️ Назад", callback_data=f"archived_page_{page-1}"))
    if len(users) == limit:
        nav_buttons.append(types.InlineKeyboardButton(text="Вперед ➡️", callback_data=f"archived_page_{page+1}"))
    
    if nav_buttons:
        builder.row(*nav_buttons)
            
    text = f"📁 {hbold('Архив учеников')} (Стр. {page + 1}):"
    if isinstance(message, types.CallbackQuery):
        await message.message.edit_text(text, reply_markup=builder.as_markup())
    else:
        await message.answer(text, reply_markup=builder.as_markup())

@admin_router.message(F.text.contains("Аналитика"), F.from_user.id.func(is_admin), StateFilter("*"))
async def admin_analytics_handler(message: types.Message, state: FSMContext):
    logger.info(f" [ADMIN] 'Analytics' handler triggered by {message.from_user.id}")
    
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
    sfi_values = [
        doc.to_dict().get('sfi_index', 1.0) 
        for doc in active_docs 
        if doc.to_dict().get('tg_id') not in ADMIN_IDS
    ]
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

@admin_router.callback_query(F.data.startswith("archived_page_"))
async def process_archived_pagination(callback: types.CallbackQuery):
    page = int(callback.data.split("_")[-1])
    await show_archived_page(callback, page)
    await callback.answer()

@admin_router.callback_query(F.data.startswith("view_archived_"))
async def view_archived_stats_handler(callback: types.CallbackQuery):
    tg_id = int(callback.data.split("_")[-1])
    user = await FirestoreDB.get_user(tg_id)
    
    if not user:
        await callback.answer("Пользователь не найден.")
        return
        
    sprint_day = 0
    if user.get('sprint_start_date'):
        td = datetime.now(timezone.utc) - user.get('sprint_start_date')
        sprint_day = td.days + 1
        
    sfi = user.get('sfi_index', 1.0)
    flags = user.get('sabotage_flags', 0)
    friction = "🔴 Критическая" if sfi < 0.2 else "🟡 Повышенная" if sfi < 0.5 else "🟢 Нормальная"

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Восстановить", callback_data=f"restore_client_{tg_id}")
    builder.button(text="📜 Логи", callback_data=f"view_logs_{tg_id}")
    builder.button(text="💀 Удалить навсегда", callback_data=f"confirm_delete_{tg_id}")
    builder.button(text="⬅️ Назад в архив", callback_data="archived_page_0")
    builder.adjust(2, 2)
    
    text = (
        f"📂 {hbold('Архивный профиль:')}\n\n"
        f"👤 Имя: {user.get('full_name')}\n"
        f"📅 День Спринта (на момент архивации): {sprint_day}/30\n"
        f"🎯 Качество (L1): {user.get('target_quality_l1')}\n\n"
        f"📈 Shadow Friction Index (SFI): {round(sfi, 2)}\n"
        f"🚩 Флаги саботажа: {flags}\n"
        f"🌡 Уровень трения: {friction}\n\n"
        f"💡 {hbold('Последний инсайт:')}\n"
        f"{user.get('last_insight') or 'Данных нет.'}"
    )
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@admin_router.callback_query(F.data.startswith("confirm_archive_"))
async def confirm_archive_client_handler(callback: types.CallbackQuery):
    tg_id = int(callback.data.split("_")[-1])
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text="📁 Перенести в архив", callback_data=f"execute_archive_{tg_id}")
    builder.button(text="⬅️ Отмена", callback_data=f"view_stats_{tg_id}")
    builder.adjust(1)
    
    text = (
        f"📂 {hbold('Архивация клиента')}\n\n"
        f"Вы подтверждаете перенос клиента {tg_id} в архив?\n"
        f"Ученик больше не будет получать уведомлений, но вся история сохранится."
    )
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@admin_router.callback_query(F.data.startswith("execute_archive_"))
async def execute_archive_handler(callback: types.CallbackQuery, bot: Bot):
    tg_id = int(callback.data.split("_")[-1])
    
    # Update status in DB
    await FirestoreDB.update_user(tg_id, {"status": "archived"})
    
    # Sync to Sheets with archived status
    user = await FirestoreDB.get_user(tg_id)
    if user:
        await sync_user_to_sheets(user)
    
    await callback.message.edit_text(f"✅ Клиент {tg_id} успешно перенесен в архив.")
    await callback.answer()

@admin_router.callback_query(F.data.startswith("restore_client_"))
async def restore_client_handler(callback: types.CallbackQuery, bot: Bot):
    tg_id = int(callback.data.split("_")[-1])
    
    # Update status back to active
    await FirestoreDB.update_user(tg_id, {"status": "active"})
    
    # Sync to Sheets
    user = await FirestoreDB.get_user(tg_id)
    if user:
        await sync_user_to_sheets(user)
        
    await callback.message.edit_text(f"✅ Клиент {tg_id} восстановлен и возвращен в общий список.")
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
    start_date = user.get('sprint_start_date') or user.get('created_at')
    
    if start_date:
        try:
            if isinstance(start_date, str):
                 # Handle potential 'Z' or other ISO formats
                 start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            
            # Ensure start_date is aware before comparison with now(utc)
            if start_date.tzinfo is None:
                start_date = start_date.replace(tzinfo=timezone.utc)
            
            delta = datetime.now(timezone.utc) - start_date
            sprint_day = max(1, delta.days + 1)
        except Exception as e:
            logger.error(f"Error calculating sprint day for {tg_id}: {e}")
            sprint_day = "Error"

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
    builder.button(text="📜 Архив отчетов", callback_data=f"view_logs_{tg_id}")
    builder.button(text="☀️ Утренний Импульс", callback_data=f"test_morning_{tg_id}")
    builder.button(text="🌙 Вечерний Отчет", callback_data=f"test_evening_{tg_id}")
    builder.button(text="⚙️ Редактировать профиль", callback_data=f"edit_profile_{tg_id}")
    builder.button(text="📁 В архив", callback_data=f"confirm_archive_{tg_id}")
    builder.button(text="⬅️ К списку", callback_data="active_page_0")
    builder.adjust(1, 1, 2, 1, 1, 1)
    
    text = (
        f"📊 {hbold('Статистика Спринта:')}\n\n"
        f"👤 Имя: {user.get('full_name')}\n"
        f"📅 День Спринта: {sprint_day}/30\n"
        f"🎯 Качество (L1): {user.get('target_quality_l1')}\n"
        f"👁 Сценарий: {user.get('scenario_type')}\n\n"
        f"📈 Shadow Friction Index (SFI): {round(sfi, 2)}\n"
        f"🚩 Флаги саботажа: {flags}\n"
        f"🌡 Уровень трения: {friction}\n\n"
        f"🌍 Часовой пояс: {user.get('timezone', 'UTC+0')}\n"
        f"💡 {hbold('Последний инсайт:')}\n"
        f"{user.get('last_insight') or 'Данных пока нет.'}"
    )
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@admin_router.callback_query(F.data.startswith("view_logs_"))
async def view_archive_handler(callback: types.CallbackQuery):
    tg_id = int(callback.data.split("_")[-1])
    user = await FirestoreDB.get_user(tg_id)
    if not user:
        await callback.answer("Клиент не найден.")
        return
        
    logs = await FirestoreDB.get_logs(user['id'], limit=5)
    
    text = f"📜 {hbold('Архив логов клиента')} {user.get('full_name')}:\n\n"
    if not logs:
        text += "Логов пока нет."
    else:
        for idx, log in enumerate(logs):
            date_str = log.get('created_at').strftime("%d.%m %H:%M") if log.get('created_at') else "N/A"
            sabotage = "🚩" if log.get('is_sabotage') else "✅"
            content = log.get('content', '')[:100] + "..." if len(log.get('content', '')) > 100 else log.get('content', '')
            text += f"{idx+1}. {sabotage} [{date_str}]: {content}\n\n"

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Назад к статистике", callback_data=f"view_stats_{tg_id}")
    
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
        await callback.answer("✅ Отправляю утренний импульс...")
        await send_morning_impulse(bot, user)
        # We can update the message text to show success too
        await callback.message.edit_text(callback.message.text + "\n\n✅ Утренний импульс отправлен!")
    else:
        await callback.answer("❌ Ошибка: клиент не найден.")

@admin_router.callback_query(F.data.startswith("test_evening_"))
async def admin_test_evening_handler(callback: types.CallbackQuery, bot: Bot):
    tg_id = int(callback.data.split("_")[-1])
    user = await FirestoreDB.get_user(tg_id)
    if user:
        await callback.answer("✅ Отправляю запрос вечернего лога...")
        await request_evening_logs(bot, user)
        await callback.message.edit_text(callback.message.text + "\n\n✅ Запрос вечернего лога отправлен!")
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

@admin_router.message(F.text.contains("Добавить клиента"), F.from_user.id.func(is_admin), StateFilter("*"))
@admin_router.message(Command("add_client"), F.from_user.id.func(is_admin), StateFilter("*"))
async def start_add_client(message: types.Message, state: FSMContext):
    logger.info(f" [ADMIN] 'Add Client' flow started by {message.from_user.id}")
    
    await state.clear() # Clear any previous state before starting new registration
    
    await state.set_state(AdminRegistration.waiting_for_username)
    await message.answer("Введите Telegram Ник (@username) нового клиента для активации:", reply_markup=get_navigation_keyboard())


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
    from aiogram.types import KeyboardButton
    builder = ReplyKeyboardBuilder()
    builder.button(text=user.get('full_name') or "Без имени")
    builder.row(KeyboardButton(text="⬅️ Назад"), KeyboardButton(text="🏠 В меню"))
    builder.adjust(1, 2)
    
    await message.answer(
        f"✅ Пользователь найден: {user.get('full_name')} (ID: {user.get('tg_id')})\n"
        f"Введите Имя для Спринта (или выберите предложенное):",
        reply_markup=builder.as_markup(resize_keyboard=True)
    )

@admin_router.message(AdminRegistration.waiting_for_full_name)
async def process_full_name(message: types.Message, state: FSMContext):
    await state.update_data(full_name=message.text)
    await state.set_state(AdminRegistration.waiting_for_quality_name)
    await message.answer("Введите название Теневого Качества (L1):", reply_markup=get_navigation_keyboard())

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
    await message.answer(text, reply_markup=get_navigation_keyboard())

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
        "Sovereign": "Твой путь к безусловной личной власти и ответственности. Возвращаем контроль и уверенно входим на 'трон' своего дела! 👑",
        "Expansion": "Расширяем горизонты и убираем любые преграды для роста. Твоя 'Большая Игра' начинается здесь и сейчас! 🚀",
        "Vitality": "Освобождаем скрытую энергию и превращаем ее в чистое топливо для твоих побед. Драйв, легкость и тотальный фокус! 🔥",
        "Architect": "Создаем идеальную систему, где каждый элемент работает на результат. Твой бизнес — это шедевр архитектуры без трения! 🏛️"
    }
    
    desc = descriptions.get(scenario_type, "Описание отсутствует.")
    
    await state.set_state(AdminRegistration.waiting_for_timezone)
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    # Common offsets for the target audience (CIS/Global)
    offsets = ["UTC-3", "UTC+0", "UTC+2", "UTC+3", "UTC+4", "UTC+5", "UTC+6", "UTC+7", "UTC+8", "UTC+9"]
    for off in offsets:
        builder.button(text=off, callback_data=f"set_tz_{off}")
    builder.adjust(3)
    
    await message.answer(
        f"Выбран сценарий: {hbold(scenario_type)}\n\n"
        f"💡 {hbold('Юз-кейс:')}\n{desc}\n\n"
        f"Теперь выберите часовой пояс клиента:",
        reply_markup=builder.as_markup()
    )

@admin_router.callback_query(AdminRegistration.waiting_for_timezone, F.data.startswith("set_tz_"))
async def process_timezone(callback: types.CallbackQuery, state: FSMContext):
    tz = callback.data.replace("set_tz_", "")
    await state.update_data(timezone=tz)
    
    data = await state.get_data()
    scenario_type = data['scenario_type']
    quality_name = data['quality_name']
    
    from aiogram.utils.keyboard import ReplyKeyboardBuilder
    builder = ReplyKeyboardBuilder()
    builder.button(text="✅ Принять")
    builder.button(text="❌ Отмена")
    builder.adjust(2)
    
    text = (
        f"📝 {hbold('Проверка данных:')}\n\n"
        f"👤 Клиент: {data.get('full_name')} (ID: {data.get('tg_id')})\n"
        f"🎯 Качество: {quality_name}\n"
        f"👁 Сценарий: {scenario_type}\n"
        f"🌍 Часовой пояс: {tz}\n\n"
        f"Активируем клиента?"
    )
    await state.set_state(AdminRegistration.waiting_for_confirmation)
    await callback.message.answer(text, reply_markup=builder.as_markup(resize_keyboard=True))
    await callback.answer()

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
        "sfi_index": 0.5, # Start with neutral friction (Yellow)
        "timezone": data.get('timezone', 'UTC+3'),
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
            f"🚀 {hbold('Поздравляю! Спринт активирован, и мы начинаем этот путь!')}\n\n"
            f"🌅 Твое движение стартует уже завтра утром. В течение дня ты будешь получать задания — просто выполняй их и фиксируй прогресс. "
            f"А каждым вечером мы будем подводить итоги: я задам пару вопросов, чтобы закрепить результат.\n\n"
            f"Мы сфокусируемся на качестве {hbold(data['quality_name'])}. Это будет увлекательное путешествие к цели! "
            f"Я рядом и верю в твой успех. Только вперед! 🔥✨"
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
    builder.button(text="🌍 Часовой пояс", callback_data="edit_field_timezone")
    builder.button(text="📅 День Спринта", callback_data="edit_field_day")
    builder.button(text="⬅️ Отмена", callback_data=f"view_stats_{client_id}")
    builder.adjust(1)
    
    await callback.message.edit_text("Что именно нужно изменить?", reply_markup=builder.as_markup())
    await callback.answer()

@admin_router.callback_query(F.data == "edit_field_timezone")
async def edit_timezone_start(callback: types.CallbackQuery, state: FSMContext):
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    offsets = ["UTC-3", "UTC+0", "UTC+2", "UTC+3", "UTC+4", "UTC+5", "UTC+6", "UTC+7", "UTC+8", "UTC+9"]
    for off in offsets:
        builder.button(text=off, callback_data=f"save_tz_{off}")
    
    data = await state.get_data()
    client_id = data.get("edit_client_id")
    builder.row(types.InlineKeyboardButton(text="⬅️ Назад", callback_data=f"edit_profile_{client_id}"))
    builder.adjust(3)
    
    await callback.message.edit_text("Выберите новый часовой пояс:", reply_markup=builder.as_markup())
    await callback.answer()

@admin_router.callback_query(F.data.startswith("save_tz_"))
async def process_edit_timezone(callback: types.CallbackQuery, state: FSMContext):
    new_tz = callback.data.replace("save_tz_", "")
    data = await state.get_data()
    client_id = data.get("edit_client_id")
    
    user = await FirestoreDB.get_user(client_id)
    if user:
        await FirestoreDB.update_user(user['id'], {"timezone": new_tz})
        await callback.message.answer(f"✅ Часовой пояс обновлен на: {hbold(new_tz)}")
        # Show stats again
        # We need to manually call it or better yet, just tell them it's done.
        # Re-triggering view_user_stats_handler might be tricky with the callback data.
    else:
        await callback.answer("Ошибка: клиент не найден.")
    
    await state.clear()

@admin_router.callback_query(F.data == "edit_field_quality")
async def edit_quality_start(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.waiting_for_edit_quality)
    await callback.message.answer("Введите новое название Теневого Качества (L1):", reply_markup=get_navigation_keyboard())
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
        f"Введите цифру (1-4):"
    )
    await callback.message.answer(text, reply_markup=get_navigation_keyboard())
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

@admin_router.callback_query(F.data == "edit_field_day")
async def edit_day_start(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.waiting_for_edit_day)
    await callback.message.answer("Введите новый номер дня (1-30):", reply_markup=get_navigation_keyboard())
    await callback.answer()

@admin_router.message(AdminStates.waiting_for_edit_day)
async def process_edit_day(message: types.Message, state: FSMContext):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("Редактирование отменено.", reply_markup=get_main_keyboard(is_admin=True))
        return
        
    if not message.text.isdigit():
        await message.answer("Пожалуйста, введите число (1-30).")
        return
        
    day = int(message.text)
    if not (1 <= day <= 30):
        await message.answer("Номер дня должен быть от 1 до 30.")
        return
        
    await state.update_data(new_day=day)
    await state.set_state(AdminStates.waiting_for_edit_day_confirm)
    
    from aiogram.utils.keyboard import ReplyKeyboardBuilder
    builder = ReplyKeyboardBuilder()
    builder.button(text="✅ Подтвердить перенос")
    builder.button(text="❌ Отмена")
    builder.adjust(2)
    
    await message.answer(
        f"Вы уверены, что хотите перевести клиента на {hbold(f'День {day}')}?\n"
        f"Клиенту будет немедленно отправлено задание этого дня.",
        reply_markup=builder.as_markup(resize_keyboard=True)
    )

@admin_router.message(AdminStates.waiting_for_edit_day_confirm)
async def process_edit_day_confirm(message: types.Message, state: FSMContext, bot: Bot):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Перенос отменен.", reply_markup=get_main_keyboard(is_admin=True))
        return
        
    if message.text != "✅ Подтвердить перенос":
        await message.answer("Пожалуйста, используйте кнопки.")
        return
        
    data = await state.get_data()
    client_id = data.get("edit_client_id")
    new_day = data.get("new_day")
    
    user = await FirestoreDB.get_user(client_id)
    if user:
        now = datetime.now(timezone.utc)
        new_start_date = now - timedelta(days=new_day - 1)
        
        await FirestoreDB.update_user(user['id'], {"sprint_start_date": new_start_date})
        
        from bot.keyboards.builders import get_day_change_action_keyboard
        await message.answer(
            f"✅ Клиент переведен на День {new_day}.\n"
            f"Что отправить клиенту сейчас?", 
            reply_markup=get_day_change_action_keyboard(client_id)
        )
    else:
        await message.answer("Ошибка: клиент не найден.")
        
    await state.clear()

@admin_router.callback_query(F.data.startswith("send_now_"))
async def handle_immediate_action(callback: types.CallbackQuery, bot: Bot):
    parts = callback.data.split("_")
    action_type = parts[2] # "morning" or "evening"
    client_id = parts[3]
    
    # Fetch user dict (scheduler functions expect dict, not ID string)
    user = await FirestoreDB.get_user(client_id)
    if not user:
        await callback.message.answer("❌ Ошибка: клиент не найден в базе данных.")
        await callback.answer()
        return

    try:
        if action_type == "morning":
            await send_morning_impulse(bot, user)
            await callback.message.answer(f"✅ Утренний импульс отправлен клиенту {user.get('full_name')}.")
        elif action_type == "evening":
            await request_evening_logs(bot, user)
            await callback.message.answer(f"✅ Запрос вечернего лога отправлен клиенту {user.get('full_name')}.")
    except Exception as e:
        import logging
        logging.error(f"Error in handle_immediate_action: {e}")
        await callback.message.answer(f"❌ Ошибка при отправке: {e}")
    
    await callback.answer()
    # Remove buttons after action
    await callback.message.edit_reply_markup(reply_markup=None)

# --- Client Deletion ---

@admin_router.callback_query(F.data.startswith("confirm_delete_"))
async def confirm_delete_client_handler(callback: types.CallbackQuery):
    tg_id = int(callback.data.split("_")[-1])
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text="💀 Да, УДАЛИТЬ НАВСЕГДА", callback_data=f"execute_delete_{tg_id}")
    builder.button(text="⬅️ Отмена", callback_data=f"view_archived_{tg_id}")
    builder.adjust(1)
    
    text = (
        f"⚠️ {hbold('ОКОНЧАТЕЛЬНОЕ УДАЛЕНИЕ')}\n\n"
        f"Вы собираетесь ПОЛНОСТЬЮ стереть данные клиента {tg_id} из системы.\n"
        f"Будут удалены:\n"
        f"• Профиль в базе данных\n"
        f"• Вся история отчетов и логов\n"
        f"• Запись в аналитической таблице\n\n"
        f"Это действие НЕОБРАТИМО. Подтверждаете?"
    )
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@admin_router.callback_query(F.data.startswith("execute_delete_"))
async def execute_delete_client_handler(callback: types.CallbackQuery, bot: Bot):
    tg_id = int(callback.data.split("_")[-1])
    
    from utils.gsheets_api import delete_user_from_sheets
    await delete_user_from_sheets(tg_id)
    await FirestoreDB.delete_user_and_data(tg_id)
    
    await callback.message.edit_text(f"💀 Клиент {tg_id} и все его данные окончательно удалены из системы.")
    await callback.answer()
    
    # 4. Optional: Notify client? (Only if bot is not blocked)
    try:
        await bot.send_message(tg_id, "ℹ️ Твой доступ к Shadow Sprint был аннулирован. Все данные удалены.")
    except:
        pass

# --- Report Review Handlers ---

@admin_router.callback_query(F.data.startswith("approve_ai_report:"))
async def approve_ai_report_handler(callback: types.CallbackQuery, bot: Bot):
    parts = callback.data.split(":")
    user_id = parts[1]
    log_id = parts[2]
    
    user = await FirestoreDB.get_user(user_id) # user_id is the document ID here from the callback
    # Wait, the callback uses user['id'] which is the doc ID. 
    # But FirestoreDB.get_user(tg_id) takes tg_id. 
    # I should check how I constructed the callback.
    # In client.py: callback_data=f"approve_ai_report:{user['id']}:{log_id}"
    # user['id'] is the doc ID.
    
    # I need a way to get user by doc ID or change client.py to use tg_id.
    # Let's add get_user_by_doc_id to FirestoreDB or use tg_id in callback.
    
    # For now, let's assume I'll fix this in next step or use doc ID directly if I can.
    # Actually, bot.send_message needs tg_id.
    
    # Let's fetch the log to get feedback
    log = await FirestoreDB.get_log(user_id, log_id)
    if not log:
        await callback.answer("❌ Ошибка: лог не найден.", show_alert=True)
        return
        
    feedback = log.get("feedback_to_client")
    
    # We need the user's tg_id to send them the message.
    # The user doc ID is useful for Firestore, but we need tg_id for Telegram.
    user_doc = FirestoreDB.db.collection("users").document(user_id).get()
    if not user_doc.exists:
        await callback.answer("❌ Ошибка: пользователь не найден.", show_alert=True)
        return
    
    tg_id = user_doc.to_dict().get("tg_id")
    
    if feedback and tg_id:
        try:
            await bot.send_message(tg_id, feedback)
            await callback.message.edit_text(f"{callback.message.text}\n\n✅ {hbold('Ответ ИИ отправлен клиенту.')}")
        except Exception as e:
            await callback.answer(f"❌ Ошибка отправки: {e}", show_alert=True)
    else:
        await callback.answer("❌ Ошибка: нет данных для отправки.", show_alert=True)
    
    await callback.answer()

@admin_router.callback_query(F.data.startswith("custom_admin_report:"))
async def custom_admin_report_start(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    user_id = parts[1] # doc ID
    log_id = parts[2]
    
    await state.update_data(custom_report_user_doc_id=user_id, custom_report_log_id=log_id)
    await state.set_state(AdminStates.waiting_for_admin_custom_report)
    
    await callback.message.answer(
        "📝 Введите ваш ответ для клиента:",
        reply_markup=get_navigation_keyboard()
    )
    await callback.answer()

@admin_router.message(AdminStates.waiting_for_admin_custom_report)
async def admin_custom_report_handler(message: types.Message, state: FSMContext, bot: Bot):
    if not is_admin(message.from_user.id): return
    
    if message.text == "🏠 В меню":
        await state.clear()
        await message.answer("Возврат в меню.", reply_markup=get_main_keyboard(is_admin=True))
        return

    data = await state.get_data()
    user_doc_id = data.get("custom_report_user_doc_id")
    log_id = data.get("custom_report_log_id")
    
    if not user_doc_id or not log_id:
        await message.answer("❌ Ошибка: данные не найдены.")
        await state.clear()
        return

    user_doc = FirestoreDB.db.collection("users").document(user_doc_id).get()
    if not user_doc.exists:
        await message.answer("❌ Ошибка: пользователь не найден.")
        await state.clear()
        return
        
    user_data = user_doc.to_dict()
    tg_id = user_data.get("tg_id")
    
    try:
        if message.text:
            if message.text == "🏠 В меню":
                await state.clear()
                await message.answer("Возврат в меню.", reply_markup=get_main_keyboard(is_admin=True))
                return
            await bot.send_message(tg_id, message.text)
            feedback_type = "text"
            feedback_val = message.text
        elif message.voice:
            await bot.send_voice(tg_id, message.voice.file_id)
            feedback_type = "voice"
            feedback_val = message.voice.file_id
        elif message.video_note:
            await bot.send_video_note(tg_id, message.video_note.file_id)
            feedback_type = "video_note"
            feedback_val = message.video_note.file_id
        else:
            await message.answer("⚠️ Я поддерживаю только текст, голосовые сообщения и видео-кружки.")
            return

        # Update log with custom response
        FirestoreDB.db.collection("users").document(user_doc_id).collection("logs").document(log_id).update({
            "feedback_to_client_custom": feedback_val,
            "feedback_type": feedback_type,
            "responded_by_admin": True
        })
        
        await message.answer(f"✅ Ваш ответ отправлен клиенту {user_data.get('full_name')}.", reply_markup=get_main_keyboard(is_admin=True))
        await state.clear()
    except Exception as e:
        await message.answer(f"❌ Ошибка при отправке: {e}")

@admin_router.message(StateFilter("*"))
async def admin_catch_all(message: types.Message):
    if not is_admin(message.from_user.id):
        return
        
    logger.info(f"❓ [ADMIN] Unmatched message from {message.from_user.id}: '{message.text}'")

