from datetime import datetime
from aiogram.filters import Command, StateFilter
from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext
from bot.states import AdminRegistration, AdminStates
from database.connection import get_db_session
from database.models import User, ShadowMap, AdminLog
from sqlalchemy import select, func
from aiogram.utils.markdown import hbold
from bot.keyboards.builders import get_main_keyboard
from config import ADMIN_IDS

from utils.scheduler import send_morning_impulse, send_weekly_briefings, request_evening_logs
from utils.gsheets_api import sync_user_to_sheets

admin_router = Router()

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

@admin_router.message(Command("trigger_morning"))
async def trigger_morning_handler(message: types.Message, bot: Bot):
    if not is_admin(message.from_user.id):
        return
    
    args = message.text.split()
    target_user = None
    
    if len(args) > 1:
        target = args[1].strip().replace("@", "")
        async with get_db_session() as session:
            if target.isdigit():
                stmt = select(User).where(User.tg_id == int(target))
            else:
                stmt = select(User).where(User.username.ilike(target))
            result = await session.execute(stmt)
            target_user = result.scalar_one_or_none()
            
            if not target_user:
                await message.answer(f"❌ Пользователь {target} не найден.")
                return
    
    if target_user:
        await message.answer(f"🚀 Запускаю утренний импульс для {target_user.full_name}...")
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
        async with get_db_session() as session:
            if target.isdigit():
                stmt = select(User).where(User.tg_id == int(target))
            else:
                stmt = select(User).where(User.username.ilike(target))
            result = await session.execute(stmt)
            target_user = result.scalar_one_or_none()
            
            if not target_user:
                await message.answer(f"❌ Пользователь {target} не найден.")
                return

    if target_user:
        await message.answer(f"🌙 Запрашиваю вечерний лог у {target_user.full_name}...")
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

@admin_router.message(F.text == "⏳ Заявки")
async def pending_list_handler(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    await show_pending_page(message)

async def show_pending_page(message: types.Message, page: int = 0):
    limit = 10
    offset = page * limit
    
    async with get_db_session() as session:
        stmt = select(User).where(User.status == "pending").limit(limit).offset(offset)
        result = await session.execute(stmt)
        users = result.scalars().all()
        
        if not users and page == 0:
            if isinstance(message, types.CallbackQuery):
                await message.message.edit_text("Список заявок пуст.")
            else:
                await message.answer("Список заявок пуст.")
            return

        from aiogram.utils.keyboard import InlineKeyboardBuilder
        builder = InlineKeyboardBuilder()
        
        for u in users:
            name = u.full_name or f"ID: {u.tg_id}"
            username = f" (@{u.username})" if u.username else ""
            builder.button(text=f"👤 {name}{username}", callback_data=f"view_pending_{u.tg_id}")
            
        builder.adjust(1)
        
        # Pagination buttons
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

@admin_router.message(F.text == "⏳ Заявки")
async def admin_pending_requests_handler(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    await show_pending_page(message)

@admin_router.message(F.text.in_({"🚀 Спринты", "👥 Клиенты"}))
async def active_sprints_handler(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    await show_active_page(message)

async def show_active_page(message: types.Message, page: int = 0):
    limit = 10
    offset = page * limit
    
    async with get_db_session() as session:
        stmt = select(User).where(User.status == "active").limit(limit).offset(offset)
        result = await session.execute(stmt)
        users = result.scalars().all()
        
        if not users and page == 0:
            if isinstance(message, types.CallbackQuery):
                await message.message.edit_text("Активных спринтов пока нет.")
            else:
                await message.answer("Активных спринтов пока нет.")
            return

        from aiogram.utils.keyboard import InlineKeyboardBuilder
        builder = InlineKeyboardBuilder()
        
        for u in users:
            name = u.full_name or f"ID: {u.tg_id}"
            sfi = f"SFI: {round(u.sfi_index or 1.0, 2)}"
            builder.button(text=f"🚀 {name} ({sfi})", callback_data=f"view_stats_{u.tg_id}")
            
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

@admin_router.message(F.text == "📊 Аналитика")
async def admin_analytics_handler(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    
    async with get_db_session() as session:
        # Get counts
        stmt_total = select(func.count(User.id))
        stmt_active = select(func.count(User.id)).where(User.status == "active")
        stmt_pending = select(func.count(User.id)).where(User.status == "pending")
        
        total_users = (await session.execute(stmt_total)).scalar()
        active_users = (await session.execute(stmt_active)).scalar()
        pending_users = (await session.execute(stmt_pending)).scalar()
        
        # Get average SFI for active users
        stmt_avg_sfi = select(func.avg(User.sfi_index)).where(User.status == "active")
        avg_sfi = (await session.execute(stmt_avg_sfi)).scalar() or 0.0
        
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
    
    async with get_db_session() as session:
        stmt = select(User).where(User.tg_id == tg_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            await callback.answer("Пользователь не найден.")
            return
            
        # Calculate Sprint Day
        sprint_day = "N/A"
        if user.sprint_start_date:
            delta = datetime.utcnow() - user.sprint_start_date
            sprint_day = delta.days + 1

        # Friction Level Logic (SFI: 0.1 goal, 1.0 critical)
        friction = "🟢 GREEN"
        if (user.sfi_index or 1.0) > 0.7 or (user.red_flags_count or 0) >= 3:
            friction = "🔴 RED"
        elif (user.sfi_index or 1.0) > 0.4 or (user.red_flags_count or 0) >= 2:
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
            f"👤 Имя: {user.full_name}\n"
            f"📅 День Спринта: {sprint_day}/30\n"
            f"🎯 Качество (L1): {user.target_quality_l1}\n"
            f"👁 Сценарий: {user.scenario_type}\n\n"
            f"📈 Shadow Friction Index (SFI): {round(user.sfi_index or 1.0, 2)}\n"
            f"🚩 Флаги саботажа: {user.red_flags_count}\n"
            f"🌡 Уровень трения: {friction}\n\n"
            f"💡 {hbold('Последний инсайт:')}\n"
            f"{user.last_insight or 'Данных пока нет.'}"
        )
        await callback.message.edit_text(text, reply_markup=builder.as_markup())
        await callback.answer()

@admin_router.callback_query(F.data.startswith("test_morning_"))
async def admin_test_morning_handler(callback: types.CallbackQuery, bot: Bot):
    tg_id = int(callback.data.split("_")[-1])
    async with get_db_session() as session:
        stmt = select(User).where(User.tg_id == tg_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        if user:
            await send_morning_impulse(bot, user)
            await callback.answer("✅ Утренний импульс отправлен!")
        else:
            await callback.answer("❌ Ошибка: клиент не найден.")

@admin_router.callback_query(F.data.startswith("test_evening_"))
async def admin_test_evening_handler(callback: types.CallbackQuery, bot: Bot):
    tg_id = int(callback.data.split("_")[-1])
    async with get_db_session() as session:
        stmt = select(User).where(User.tg_id == tg_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        if user:
            await request_evening_logs(bot, user)
            await callback.answer("✅ Вечерний лог-запрос отправлен!")
        else:
            await callback.answer("❌ Ошибка: клиент не найден.")

@admin_router.callback_query(F.data.startswith("view_pending_"))
async def view_pending_user(callback: types.CallbackQuery):
    tg_id = int(callback.data.split("_")[-1])
    
    async with get_db_session() as session:
        stmt = select(User).where(User.tg_id == tg_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        
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
            f"Имя: {user.full_name}\n"
            f"Username: @{user.username or 'N/A'}\n"
            f"TG ID: {user.tg_id}\n\n"
            f"Выбери действие:"
        )
        await callback.message.edit_text(text, reply_markup=builder.as_markup())
        await callback.answer()

@admin_router.callback_query(F.data.startswith("reject_user_"))
async def reject_user_handler(callback: types.CallbackQuery, bot: Bot):
    tg_id = int(callback.data.split("_")[-1])
    async with get_db_session() as session:
        stmt = select(User).where(User.tg_id == tg_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        if user:
            user.status = "rejected"
            await session.commit()
            try:
                await bot.send_message(tg_id, "❌ К сожалению, твоя заявка на активацию Спринта была отклонена.")
            except: pass
            
    await callback.message.edit_text("❌ Заявка отклонена.")
    await callback.answer()

@admin_router.callback_query(F.data.startswith("approve_user_"))
async def approve_user_start_registration(callback: types.CallbackQuery, state: FSMContext):
    tg_id = int(callback.data.split("_")[-1])
    # Pre-fill FSM and start the registration questions
    await state.update_data(tg_id=tg_id)
    
    async with get_db_session() as session:
        stmt = select(User).where(User.tg_id == tg_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        if user:
            await state.update_data(full_name=user.full_name)
    
    await state.set_state(AdminRegistration.waiting_for_quality_name)
    await callback.message.answer(f"Начинаем регистрацию для ID {tg_id}.\nВведите название Теневого Качества (L1):")
    await callback.answer()

@admin_router.message(Command("add_client"))
async def start_add_client(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    await state.set_state(AdminRegistration.waiting_for_username)
    await message.answer("Введите Telegram Ник (@username) нового клиента:")

@admin_router.message(AdminRegistration.waiting_for_username)
async def process_username(message: types.Message, state: FSMContext):
    username = message.text.strip().replace("@", "")
    
    async with get_db_session() as session:
        stmt = select(User).where(User.username.ilike(username))
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            await message.answer(
                f"❌ Пользователь с ником @{username} не найден в базе бота.\n\n"
                f"Клиент должен сначала запустить бота (/start), чтобы мы могли его активировать. "
                f"Попробуйте другой ник или попросите его нажать /start."
            )
            return
        
        await state.update_data(tg_id=user.tg_id)
        await state.set_state(AdminRegistration.waiting_for_full_name)
        
        # Suggested name button
        from aiogram.utils.keyboard import ReplyKeyboardBuilder
        builder = ReplyKeyboardBuilder()
        builder.button(text=user.full_name or "Без имени")
        builder.adjust(1)
        
        await message.answer(
            f"✅ Пользователь найден: {user.full_name} (ID: {user.tg_id})\n"
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
    
    async with get_db_session() as session:
        # Create ShadowMap
        shadow_map = ShadowMap(
            quality_name=data['quality_name'],
            potential_desc="" 
        )
        session.add(shadow_map)
        await session.flush()
        
        # Create or Update User
        stmt = select(User).where(User.tg_id == data['tg_id'])
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            user = User(
                tg_id=data['tg_id'],
                full_name=data['full_name'],
                shadow_map_id=shadow_map.id,
                role="client",
                scenario_type=scenario_type,
                target_quality_l1=data['quality_name'],
                status="active",
                sfi_index=1.0, 
                sprint_start_date=datetime.utcnow()
            )
            session.add(user)
        else:
            user.full_name = data['full_name']
            user.shadow_map_id = shadow_map.id
            user.role = "client"
            user.status = "active"
            user.scenario_type = scenario_type
            user.target_quality_l1 = data['quality_name']
            if not user.sprint_start_date:
                user.sprint_start_date = datetime.utcnow()
        
        await session.commit()
    
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
        reply_markup=get_main_keyboard()
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
    
    async with get_db_session() as session:
        stmt = select(User).where(User.tg_id == client_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if user:
            user.target_quality_l1 = new_quality
            await session.commit()
            
            # Sync to Sheets
            await sync_user_to_sheets({
                "user_id": user.tg_id,
                "name": user.full_name,
                "target_quality": new_quality,
                "scenario": user.scenario_type,
                "red_flags": user.red_flags_count or 0,
                "sfi_index": user.sfi_index or 1.0
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
    
    async with get_db_session() as session:
        stmt = select(User).where(User.tg_id == client_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if user:
            user.scenario_type = new_scenario
            await session.commit()
            
            # Sync to Sheets
            await sync_user_to_sheets({
                "user_id": user.tg_id,
                "name": user.full_name,
                "target_quality": user.target_quality_l1,
                "scenario": new_scenario,
                "red_flags": user.red_flags_count or 0,
                "sfi_index": user.sfi_index or 1.0
            })
            
            await message.answer(f"✅ Сценарий изменен на: {hbold(new_scenario)}", reply_markup=get_main_keyboard(is_admin=True))
        else:
            await message.answer("Ошибка: клиент не найден.")
            
    await state.clear()
