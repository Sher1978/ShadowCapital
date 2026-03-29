from aiogram import Router, types, F, Bot
from aiogram.filters import CommandStart, Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.utils.markdown import hbold, hitalic, hunderline, hcode
from database.firebase_db import FirestoreDB
from bot.keyboards.builders import get_main_keyboard
from aiogram.utils.keyboard import InlineKeyboardBuilder
import os
import logging
from utils.transcription import transcribe_voice
from utils.analysis import analyze_sabotage
from utils.alerts import send_red_alert
from utils.gsheets_api import sync_user_to_sheets, sync_sfi_analytics, get_instruction_text, get_test_answers
from utils.sfi_logic import calculate_daily_sfi, get_sfi_zone
from config import ADMIN_IDS, MENU_KEYWORDS, is_admin
from datetime import datetime, timezone, time
import random

client_router = Router()


async def notify_admin_of_report(bot: Bot, user: dict, content: str, analysis: dict, log_id: str):
    """Sends a detailed client report to all administrators in Vietnam (UTC+7) time."""
    from utils.timezone_utils import get_now_in_tz, adjust_to_tz
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    
    # User-requested default: Vietnam (UTC+7)
    now_vn = get_now_in_tz("UTC+7")
    
    # Calculate sprint day using Vietnam time for consistency
    start_date = user.get('sprint_start_date') or user.get('created_at')
    day = "N/A"
    if start_date:
        try:
            # Adjust start_date to VN time before comparing
            start_date_vn = adjust_to_tz(start_date, "UTC+7")
            day = (now_vn.date() - start_date_vn.date()).days + 1
            day = max(1, day)
        except:
            day = "Error"

    admin_msg = (
        f"📩 {hbold('НОВЫЙ ОТЧЕТ КЛИЕНТА')}\n\n"
        f"👤 {hbold('Имя:')} {user.get('full_name')}\n"
        f"📅 {hbold('Дата:')} {now_vn.strftime('%d.%m.%Y')}\n"
        f"⏰ {hbold('Время:')} {now_vn.strftime('%H:%M')} (VN)\n"
        f"🚀 {hbold('День программы:')} {day}\n\n"
        f"📝 {hbold('Текст отчета:')}\n{hitalic(content)}\n\n"
        f"🤖 {hbold('Ответ бота (Scan):')}\n{analysis.get('feedback_to_client', 'Нет ответа')}\n\n"
        f"📉 {hbold('SFI Score:')} {analysis.get('sfi_score', 'N/A')}"
    )

    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Отправить ответ ИИ", callback_data=f"approve_ai_report:{user['id']}:{log_id}")
    builder.button(text="📝 Свой ответ", callback_data=f"custom_admin_report:{user['id']}:{log_id}")
    builder.adjust(1)

    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, admin_msg, reply_markup=builder.as_markup())
        except Exception as e:
            logging.error(f"Failed to notify admin {admin_id} of report: {e}")

@client_router.message(CommandStart())
@client_router.message(Command("menu"))
@client_router.message(F.text == "🏠 В меню")
async def command_start_handler(message: types.Message, command: CommandObject = None) -> None:
    is_admin_user = message.from_user.id in ADMIN_IDS
    
    # Handle Deep Linking (SFI Result)
    if command and command.args:
        args = command.args
        if args.startswith("W-"):
            await handle_sfi_deep_link(message, args)
            return

    user = await FirestoreDB.get_user(message.from_user.id)
    
    if not user:
        user_data = {
            "tg_id": message.from_user.id,
            "username": message.from_user.username,
            "full_name": message.from_user.full_name,
            "role": "admin" if is_admin_user else "client",
            "status": "active" if is_admin_user else "new",
            "sfi_index": 0.5,
            "red_flags_count": 0
        }
        doc_id = await FirestoreDB.create_user(user_data)
        user = user_data
        user['id'] = doc_id
        
    is_active = (user.get('status') == "active") or is_admin_user
    
    await message.answer(
        f"Привет, {hbold(message.from_user.full_name)}! Бот Shadow Guardian на связи.\n"
        f"Если ты участник Shadow Sprint, я буду сопровождать тебя ближайшие 30 дней.",
        reply_markup=get_main_keyboard(is_admin_user, is_active=is_active)
    )

async def handle_sfi_deep_link(message: types.Message, uuid: str):
    """Handles logic when user comes from SFI Web Test."""
    lead = await FirestoreDB.get_sfi_lead(uuid)
    if not lead:
        builder = InlineKeyboardBuilder()
        builder.button(text="📝 Пройти тест", url="https://shershadow.web.app/sfitest")
        await message.answer(
            f"❌ Код доступа {hcode(uuid)} недействителен или срок его действия истек.",
            reply_markup=builder.as_markup()
        )
        return

    sfi = lead.get('sfi_score', 0)
    archetype = lead.get('archetype', 'Unknown')
    zone_scores = lead.get('zone_scores', {}) # Map: {Vitality: 15, Sovereign: 20...}
    
    # Fetch dynamic summaries from GSheets
    summaries_data = await get_test_answers()
    
    def get_summary(zone_name, score_30):
        # Convert 0-30 to 0-10
        score_10 = round(score_30 / 3.0, 1)
        intensity = "1-5"
        if score_10 > 8: intensity = "9-10"
        elif score_10 > 5: intensity = "6-8"
        
        for row in summaries_data:
            if row.get('Scenario') == zone_name and row.get('Range') == intensity:
                return row.get('Summary', 'N/A'), score_10
        return "Диагностика в этой зоне подтверждает наличие Теневого Капитала.", score_10

    # Zone mapping for display
    zones_meta = [
        ("Sovereign", "👑 Sovereign (Власть и Границы)"),
        ("Expansion", "📈 Expansion (Наглость и Масштаб)"),
        ("Vitality", "🔋 Vitality (Ресурс и Энергия)"),
        ("Architect", "👁 Architect (Интуиция и Хаос)")
    ]
    
    diagnostic_blocks = []
    for internal_name, display_name in zones_meta:
        score_30 = zone_scores.get(internal_name, 0)
        summary_text, s10 = get_summary(internal_name, score_30)
        diagnostic_blocks.append(
            f"{hbold(display_name)}: {s10}/10\n"
            f"{hitalic(summary_text)}"
        )
    
    full_diagnostic = "\n\n".join(diagnostic_blocks)
    
    welcome_text = (
        f"🗝 {hbold('ДОСТУП ОТКРЫТ: ВАШ SFI ДОСЬЕ')}\n\n"
        f"Я получил результаты твоего сканирования из системы SFI Web.\n\n"
        f"📊 {hbold('Итоговый SFI Index:')} {sfi}%\n"
        f"🏆 {hbold('Ведущий Архетип:')} {archetype}\n\n"
        f"📝 {hbold('ПОЛНАЯ ДИАГНОСТИКА:')}\n\n"
        f"{full_diagnostic}\n"
        f"\n{hbold('Рекомендован личный аудит')}\n\n"
        "Твои результаты получены и обрабатываются. Это первый шаг к конвертации Теневого Капитала в реальный. "
        "Ожидай сообщения, мы уже анализируем твою стратегию."
    )
    
    await message.answer(welcome_text)
    
    # Notify admin with full details
    bot = message.bot
    admin_notification = (
        f"🚨 {hbold('SFI РЕЗУЛЬТАТ ПРИВЯЗАН')}\n\n"
        f"👤 {message.from_user.full_name} (@{message.from_user.username or 'N/A'}) "
        f"привязал свой SFI результат {hbold(uuid)}!\n\n"
        f"📊 {hbold('Итоговый SFI Index:')} {sfi}%\n"
        f"🏆 {hbold('Ведущий Архетип:')} {archetype}\n\n"
        f"📝 {hbold('ПОЛНАЯ ДИАГНОСТИКА:')}\n\n"
        f"{full_diagnostic}"
    )
    
    for admin_id in ADMIN_IDS:
        # Avoid sending the same message twice if the user themselves is an admin
        if admin_id == message.from_user.id:
            continue
            
        try:
            await bot.send_message(admin_id, admin_notification)
        except: pass

@client_router.message(F.text.contains("Активировать Спринт"))
async def activate_request_handler(message: types.Message):
    user = await FirestoreDB.get_user(message.from_user.id)
    
    if not user:
        await command_start_handler(message)
        return

    status = user.get('status')
    if status == "active":
        await message.answer("✅ Твой Shadow Sprint уже в разгаре! Используй кнопки ниже для работы.")
        return
    if status == "pending":
        await message.answer("⏳ Твоя заявка на рассмотрении. Ожидай уведомления от куратора.")
        return
            
    text = (
        "Перед активацией твоего профиля в системе Sher | Shadow Capital, "
        "тебе необходимо принять Правила и Политику программы Shadow Sprint.\n\n"
        f"{hbold('Краткие положения:')}\n"
        "🌑 Confidentiality: Двусторонний NDA на всю информацию и методики.\n"
        "📊 Discipline: Обязательный ежедневный отчет по формуле С.И.К. до 20:00.\n"
        "📉 SFI Control: 3 красных флага за саботаж = исключение без возврата средств.\n\n"
        "Нажимая кнопку ниже, ты подтверждаешь свою готовность к работе по этим стандартам."
    )
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text="📜 Читать полные правила", url="https://telegra.ph/Shadow-Sprint-Rules-03-17") # Placeholder URL or just text
    builder.button(text="✅ Ознакомлен и принимаю правила", callback_data="accept_rules")
    builder.adjust(1)
    
    await message.answer(text, reply_markup=builder.as_markup())

@client_router.callback_query(F.data == "accept_rules")
async def accept_rules_handler(callback: types.CallbackQuery, bot: Bot):
    user = await FirestoreDB.get_user(callback.from_user.id)
    
    if not user or user.get('status') == "active" or user.get('status') == "pending":
        await callback.answer("Твой статус уже обновлен.")
        return

    update_data = {
        "rules_accepted": True,
        "rules_accepted_at": datetime.now(timezone.utc),
        "status": "pending"
    }
    await FirestoreDB.update_user(user['id'], update_data)
    
    await callback.message.edit_text(
        "✅ Твои правила приняты. Запрос на активацию Спринта отправлен куратору.\n"
        "После подтверждения тебе придет уведомление и откроется доступ к заданиям."
    )
    await callback.answer("Правила приняты!")
        
    # Notify Admins
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text="📂 Открыть заявки", callback_data="pending_page_0")
    
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"🔔 {hbold('Новая заявка на активацию!')}\n\n"
                f"От: {callback.from_user.full_name} (@{callback.from_user.username or 'N/A'})\n"
                f"ID: {callback.from_user.id}\n\n"
                f"Нажми кнопку ниже, чтобы рассмотреть.",
                reply_markup=builder.as_markup()
            )
        except: pass

@client_router.callback_query(F.data == "morning_confirm")
async def morning_confirm_handler(callback: types.CallbackQuery):
    user = await FirestoreDB.get_user(callback.from_user.id)
    if not user:
        await callback.answer("Пользователь не найден.")
        return
        
    update_data = {
        "last_confirmation_at": datetime.now(timezone.utc)
    }
    await FirestoreDB.update_user(user['id'], update_data)
    
    # Extract original text and append confirmation
    original_text = callback.message.text or callback.message.caption or ""
    
    # Preserve the buttons (keeping only "Submit Log" if we want, or both)
    # The user says "These buttons should not disappear"
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    # We can mark the first button as active/disabled or just keep it
    builder.button(text="✅ Готов (зафиксировано)", callback_data="morning_already_confirmed")
    builder.button(text="📝 Сдать отчет сейчас", callback_data="start_early_log")
    builder.adjust(1)

    await callback.message.edit_text(
        f"{original_text}\n\n✅ {hbold('Принято! Твоя готовность зафиксирована. Действуй!')}",
        reply_markup=builder.as_markup()
    )
    await callback.answer("Готовность подтверждена!")

@client_router.callback_query(F.data == "morning_already_confirmed")
async def morning_already_confirmed_handler(callback: types.CallbackQuery):
    await callback.answer("Ты уже подтвердил готовность на сегодня! 🚀", show_alert=True)

    user = await FirestoreDB.get_user(callback.from_user.id)
    if not user: return
    
    # Notify Admins
    from aiogram import Bot
    bot = callback.bot
    client_name = user.get('full_name', "N/A")
    confirm_time = datetime.now(timezone.utc).strftime("%H:%M")
    
    original_text = callback.message.text or callback.message.caption or ""
    
    # Try to extract just the task body (between greetings and footer)
    task_text = original_text
    lines = original_text.split('\n\n')
    if len(lines) >= 3:
        # Based on utils/scheduler.py structure: [greeting, quality:impulse, task_body, footer]
        # We want the 3rd block (index 2)
        task_text = lines[2]

    admin_msg = (
        f"✅ {hbold('Задача принята!')}\n\n"
        f"👤 {hbold('Клиент:')} {client_name}\n"
        f"⏰ {hbold('Время:')} {confirm_time} UTC\n"
        f"📝 {hbold('Задание:')}\n{task_text}"
    )

    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, admin_msg)
        except Exception as e:
            logging.error(f"Failed to notify admin {admin_id} about task acceptance: {e}")

@client_router.message(F.text == "📖 Инструкция")
async def instruction_handler(message: types.Message) -> None:
    from utils.gsheets_api import get_instruction_text
    text = await get_instruction_text()
    await message.answer(text, parse_mode="Markdown")

@client_router.message(F.text == "🎯 Моя цель")
async def my_goal_handler(message: types.Message) -> None:
    user = await FirestoreDB.get_user(message.from_user.id)
    
    if not user or not user.get('target_quality_l1'):
        await message.answer("Твой Shadow Sprint еще не активирован. Ожидай регистрации куратором.")
        return
        
    text = (
        f"Твоя текущая цель:\n\n"
        f"🎯 {hbold('Качество:')} {user.get('target_quality_l1')}\n"
        f"✨ {hbold('Золотой потенциал:')}\n{hitalic(user.get('potential_desc', 'N/A'))}"
    )
    await message.answer(text)

@client_router.message(F.text == "📈 Мои результаты")
async def my_results_handler(message: types.Message) -> None:
    user = await FirestoreDB.get_user(message.from_user.id)
    
    if not user:
        return

    # Calculate sprint day
    sprint_day = "Не начат"
    start_date = user.get('sprint_start_date')
    if start_date:
        if isinstance(start_date, datetime):
            delta = datetime.now() - start_date
        else: # Firestore might return a Timestamp object or string
            delta = datetime.now() - start_date
        sprint_day = f"День {delta.days + 1}"

    text = (
        f"📈 {hbold('Твой прогресс Shadow Sprint')}:\n\n"
        f"🚀 {hbold('Этап:')} {sprint_day}\n"
        f"📉 {hbold('SFI Index:')} {round(user.get('sfi_index', 1.0), 2)}\n"
        f"🚩 {hbold('Красные флаги:')} {user.get('red_flags_count', 0)} / 3\n\n"
        "Твой SFI Index показывает текущий уровень саботажа (чем ниже число, тем меньше сопротивления). "
        "3 красных флага ведут к исключению из программы."
    )
    
    last_insight = user.get('last_insight')
    if last_insight:
        text += f"\n\n💡 {hbold('Последний инсайт:')}\n{hitalic(last_insight)}"
        
    await message.answer(text)

@client_router.message(F.text == "❓ Вопрос куратору")
async def curator_question_handler(message: types.Message, bot: Bot):
    user = await FirestoreDB.get_user(message.from_user.id)
    
    if not user:
        return

    await send_red_alert(
        bot,
        user.get('full_name', "Клиент"),
        user.get('tg_id'),
        "QUESTION",
        "Запрос связи с куратором",
        "Нажата кнопка 'Вопрос куратору' в боте."
    )
        
    await message.answer(
        "❓ Твой вопрос отправлен куратору. \n\n"
        "Мы свяжемся с тобой в ближайшее время. "
        "Пока можешь сформулировать вопрос подробнее или просто подождать ответа."
    )


async def trigger_shadow_log_prompt(message: types.Message):
    """Refactored helper to show the report prompt."""
    text = (
        f"{hbold('📝 ВЕЧЕРНИЙ ОТЧЕТ')}\n\n"
        "Это пространство для твоей честности. Вспомни сегодняшний день:\n\n"
        "❓ КАК СЕГОДНЯ ПРОЯВИЛОСЬ ТВОЕ ТЕНЕВОЕ КАЧЕСТВО?\n\n"
        "❓ СТОЛКНУЛСЯ ЛИ ТЫ С СОПРОТИВЛЕНИЕМ?\n\n"
        "❓ КАКИЕ ИНСАЙТЫ ИЛИ 'ТЕНИ' ТЫ ЗАМЕТИЛ?\n\n"
        f"{hitalic('Пришли текстовое или голосовое сообщение прямо сейчас.')}\n\n"
        "Бот проанализирует его на предмет саботажа и даст обратную связь."
    )
    from aiogram.utils.keyboard import ReplyKeyboardBuilder
    builder = ReplyKeyboardBuilder()
    builder.button(text="🏠 В меню")
    await message.answer(text, reply_markup=builder.as_markup(resize_keyboard=True))

@client_router.message(F.text == "📝 Вечерний Отчет")
async def shadow_log_prompt_handler(message: types.Message):
    user = await FirestoreDB.get_user(message.from_user.id)
    if not user: return
    
    today_log = await FirestoreDB.get_today_log(user['id'])
    if today_log:
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        builder = InlineKeyboardBuilder()
        builder.button(text="🔄 Пересдать отчет", callback_data="re_submit_log")
        builder.button(text="🏠 В меню", callback_data="back_to_menu")
        builder.adjust(1)
        await message.answer("⚠️ Ты уже сдал отчет сегодня. Хочешь обновить его?", reply_markup=builder.as_markup())
        return

    await trigger_shadow_log_prompt(message)

@client_router.callback_query(F.data == "start_early_log")
@client_router.callback_query(F.data == "start_evening_log")
async def start_log_callback(callback: types.CallbackQuery):
    user = await FirestoreDB.get_user(callback.from_user.id)
    if not user: 
        await callback.answer("Профиль не найден.")
        return
        
    today_log = await FirestoreDB.get_today_log(user['id'])
    if today_log:
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        builder = InlineKeyboardBuilder()
        builder.button(text="🔄 Пересдать отчет", callback_data="re_submit_log")
        builder.button(text="🏠 В меню", callback_data="back_to_menu")
        builder.adjust(1)
        await callback.message.answer("⚠️ Ты уже сдал отчет сегодня. Хочешь обновить его?", reply_markup=builder.as_markup())
    else:
        await trigger_shadow_log_prompt(callback.message)
    await callback.answer()

@client_router.callback_query(F.data == "back_to_menu")
async def back_to_menu_callback(callback: types.CallbackQuery, state: FSMContext = None):
    if state:
        await state.clear()
    await callback.message.delete()
    is_user_admin = is_admin(callback.from_user.id)
    # Simple menu return - user is active if they are here
    await callback.message.answer("Возврат в меню.", reply_markup=get_main_keyboard(is_admin=is_user_admin, is_active=True))
    await callback.answer()

@client_router.callback_query(F.data == "re_submit_log")
async def re_submit_log_callback(callback: types.CallbackQuery):
    await callback.message.edit_reply_markup(reply_markup=None)
    await trigger_shadow_log_prompt(callback.message)
    await callback.answer()

@client_router.message(F.voice | F.audio | (F.text & ~F.text.in_(MENU_KEYWORDS)))
async def log_handler(message: types.Message, bot: Bot, state: FSMContext):
    user = await FirestoreDB.get_user(message.from_user.id)
    
    if not user:
        logging.info(f"📩 [LOG] User {message.from_user.id} not found in DB")
        return
        
    role = user.get('role', 'none')
    logging.info(f"📩 [LOG] User {message.from_user.id} (Role: {role}) sent log: {message.text or 'VOICE'}")

    if role not in ["client", "admin"]:
        await message.answer(f"⚠️ Твой аккаунт ({role}) не активирован для сдачи отчетов. Обратись к администратору.")
        return

    is_voice = message.voice is not None or message.audio is not None
    file_id = None
    content = message.text
    
    if is_voice:
        try:
            file_id = message.voice.file_id if message.voice else message.audio.file_id
            await message.answer("🔊 Обрабатываю твое голосовое сообщение...")
            
            import tempfile
            temp_dir = tempfile.gettempdir()
            perm_path = os.path.join(temp_dir, f"{file_id}.ogg")
            
            file = await bot.get_file(file_id)
            await bot.download_file(file.file_path, perm_path)
            content = await transcribe_voice(perm_path)
            
            if os.path.exists(perm_path):
                os.remove(perm_path)
            
            from aiogram.utils.keyboard import InlineKeyboardBuilder
            builder = InlineKeyboardBuilder()
            builder.button(text="✅ Отправить", callback_data="confirm_log")
            builder.button(text="🔄 Изменить", callback_data="edit_log")
            builder.adjust(2)
            
            from bot.states import ClientStates
            await state.update_data(temp_log_content=content, is_voice=True, file_id=file_id)
            await state.set_state(ClientStates.waiting_for_log_confirmation)
            
            await message.answer(
                f"📝 {hbold('Расшифровка твоего сообщения:')}\n\n"
                f"{hitalic(content or 'Голос не распознан')}\n\n"
                f"Все верно? Если да, нажми Отправить.",
                reply_markup=builder.as_markup()
            )
            return
            
        except Exception as e:
            logging.error(f"❌ Error processing voice message: {e}", exc_info=True)
            await message.answer("⚠️ Не удалось обработать голосовое сообщение. Пожалуйста, попробуй отправить текст.")
            return
    
    if not content:
        content = "Empty Log"

    await process_shadow_log(message, bot, user, content, is_voice, file_id)

async def process_shadow_log(message: types.Message, bot: Bot, user: dict, content: str, is_voice: bool, file_id: str = None):
    """
    Core logic for processing a shadow log (text or confirmed voice).
    """
    status_msg = await message.answer("⌛️ Анализирую твой отчет...")

    from utils.analysis import analyze_sabotage
    analysis = await analyze_sabotage(
        content, 
        quality_name=user.get('target_quality_l1', "Unknown"),
        scenario_type=user.get('scenario_type', "N/A")
    )
    
    try: await status_msg.delete()
    except: pass

    # --- SFI LOGIC ---
    from utils.timezone_utils import get_now_in_tz
    user_tz = user.get('timezone', 'UTC+7')
    now_user = get_now_in_tz(user_tz)
    
    # Fetch Task Engine 2.0 data for Guard Trap and Level
    from utils.gsheets_api import get_task_2_0
    start_date = user.get('sprint_start_date') or user.get('created_at')
    if isinstance(start_date, str):
        try: start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        except: start_date = datetime.now(timezone.utc)
    
    day = (datetime.now(timezone.utc) - start_date).days + 1
    task_data = await get_task_2_0(day, user.get('scenario_type', 'Sovereign'))
    guard_trap = task_data.get('guard_trap', '') if task_data else ""
    
    # Re-run analysis with Guard Trap if available
    if guard_trap:
        analysis = await analyze_sabotage(
            content, 
            quality_name=user.get('target_quality_l1', "Unknown"),
            scenario_type=user.get('scenario_type', "N/A"),
            guard_trap=guard_trap
        )

    penalty = 0
    if now_user.time() > time(20, 0):
        penalty = 5

    # L (Level) comes from user choice
    l_val = user.get('current_day_level', 2) # Default to 2 if not chosen
    
    math_sfi = calculate_daily_sfi(
        level=l_val,
        status=analysis.get('status', 1),
        penalty=penalty
    )
    s_zone = get_sfi_zone(math_sfi)

    def get_shadow_insight(zone):
        insights_path = "docs/Shadow_Insights.md"
        if not os.path.exists(insights_path):
            return "✅ Отчет принят."
        try:
            with open(insights_path, "r", encoding="utf-8") as f:
                content = f.read()
            zone_headers = {"RED": "## 🔴 КРАСНАЯ ЗОНА", "YELLOW": "## 🟡 ЖЕЛТАЯ ЗОНА", "GREEN": "## 🟢 ЗЕЛЕНАЯ ЗОНА"}
            header = zone_headers.get(zone)
            if not header: return "Отчет принят."
            sections = content.split("##")
            for sec in sections:
                if sec.strip().startswith(header.replace("##", "").strip()):
                    lines = [line.strip("- ").strip() for line in sec.split("\n") if line.strip().startswith("-")]
                    if lines: return random.choice(lines)
            return "Отчет принят."
        except: return "Отчет принят."

    insight_msg = get_shadow_insight(s_zone)

    log_data = {
        "content": content,
        "is_voice": is_voice,
        "file_id": file_id,
        "local_file_path": None,
        "is_sabotage": analysis.get("is_sabotage", False),
        "sfi_score": math_sfi,
        "llm_sfi": analysis.get("sfi_score", 0.5),
        "level": analysis.get('level', 2),
        "status": analysis.get('status', 1),
        "discomfort": analysis.get('discomfort', 5),
        "penalty": penalty,
        "feedback_to_client": analysis.get("feedback_to_client", ""),
        "analysis_reason": analysis.get("internal_analysis", "")
    }
    log_id = await FirestoreDB.add_log(user['id'], log_data)
    
    previous_logs = await FirestoreDB.get_logs(user['id'], limit=5)
    
    if len(previous_logs) >= 3:
        sfi_history = [l.get('sfi_score', 0.5) for l in previous_logs[:3]]
        if len(sfi_history) == 3 and sfi_history[0] < sfi_history[1] < sfi_history[2]:
            await message.answer(f"✨ {hbold('Shadow Growth Detected!')} Вижу, как твое сопротивление тает. Ты в потоке.")

    if math_sfi > 70:
        for admin_id in ADMIN_IDS:
             try:
                 await bot.send_message(admin_id, f"🚩 {hbold('SFI ALERT')}: {user.get('full_name')} -> {math_sfi}%")
             except: pass

    if len(previous_logs) >= 2:
        sfi_2day = [l.get('sfi_score', 0.5) for l in previous_logs[:2]]
        if all(s > 80 for s in sfi_2day):
            for admin_id in ADMIN_IDS:
                try:
                    await bot.send_message(admin_id, f"🚨 {hbold('EMERGENCY SOS')}: {user.get('full_name')} (>80% 2 дня).")
                except: pass
            await message.answer(f"🆘 {hbold('Внимание:')} Твой уровень сопротивления критичен. Куратор назначил тебе экстренный созвон.")

    update_data = {
        "sfi_index": math_sfi / 100.0,
        "last_insight": analysis.get("last_insight", "")
    }
    
    if analysis.get("is_sabotage", False):
        update_data["red_flags_count"] = user.get('red_flags_count', 0) + 1
        await send_red_alert(bot, user.get('full_name'), user.get('tg_id'), "SABOTAGE", analysis.get("internal_analysis", ""), content)
    
    await FirestoreDB.update_user(user['id'], update_data)
    await sync_user_to_sheets({
        "user_id": user.get('tg_id'),
        "name": user.get('full_name'),
        "target_quality": user.get('target_quality_l1'),
        "scenario": user.get('scenario_type'),
        "red_flags": update_data.get("red_flags_count", user.get('red_flags_count', 0)),
        "sfi_index": math_sfi / 100.0,
        "last_insight": update_data["last_insight"]
    })
    
    await sync_sfi_analytics({
        "user_id": user.get('tg_id'), "name": user.get('full_name'),
        "date": now_user.strftime("%Y-%m-%d"), "level": analysis.get('level'),
        "status": analysis.get('status'), "discomfort": analysis.get('discomfort'),
        "penalty": penalty, "sfi_score": math_sfi, "zone": s_zone
    })
        
    await notify_admin_of_report(bot, user, content, analysis, log_id)
    
    # Clear level after report
    await FirestoreDB.update_user(user['id'], {"current_day_level": 2})
    
    await message.answer(f"{insight_msg}\n\nПожалуйста, дождись комментария Администратора.")

@client_router.callback_query(F.data.startswith("task_level:"))
async def task_level_selection_handler(callback: types.CallbackQuery, bot: Bot):
    level_key = callback.data.split(":")[1] # light, medium, hard
    
    user = await FirestoreDB.get_user(callback.from_user.id)
    if not user: return
    
    # Fetch task text
    from utils.gsheets_api import get_task_2_0
    
    start_date = user.get('sprint_start_date') or user.get('created_at')
    if isinstance(start_date, str):
        try: start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        except: start_date = datetime.now(timezone.utc)
        
    day = (datetime.now(timezone.utc) - start_date).days + 1
    task_data = await get_task_2_0(day, user.get('scenario_type', 'Sovereign'))
    
    if not task_data:
        await callback.answer("Ошибка: данные задания не найдены.")
        return
        
    task_text = task_data.get(f"task_{level_key}")
    phase_text = f"{hitalic(task_data.get('phase'))}\n\n" if task_data.get('phase') else ""
    level_names = {"light": "◽️ Light", "medium": "🔶 Medium", "hard": "🔥 Hard"}
    
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить", callback_data=f"task_confirm:{level_key}")
    builder.button(text="🔄 Выбрать Другое", callback_data="change_task_level")
    builder.adjust(1)
    
    await callback.message.edit_text(
        f"🎯 {hbold('Выбранный уровень:')} {level_names[level_key]}\n\n"
        f"{phase_text}"
        f"{hbold('Задание:')}\n{task_text}\n\n"
        f"Подтверждаешь свой выбор на сегодня?",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@client_router.callback_query(F.data.startswith("task_confirm:"))
async def task_level_confirm_handler(callback: types.CallbackQuery, bot: Bot):
    level_key = callback.data.split(":")[1]
    level_map = {"light": 1, "medium": 2, "hard": 3}
    l_val = level_map.get(level_key, 2)
    level_names = {"light": "◽️ Light", "medium": "🔶 Medium", "hard": "🔥 Hard"}

    user = await FirestoreDB.get_user(callback.from_user.id)
    if not user: return
    
    # Update user choice in DB
    await FirestoreDB.update_user(user['id'], {"current_day_level": l_val})
    
    # Notify Admins
    client_name = user.get('full_name', "N/A")
    confirm_time = datetime.now(timezone.utc).strftime("%H:%M")
    
    # Extract task text for admin notification
    original_text = callback.message.text or ""
    task_text = "N/A"
    if "Задание:\n" in original_text:
        task_text = original_text.split("Задание:\n")[1].split("\n\nПодтверждаешь")[0]

    admin_msg = (
        f"✅ {hbold('Задача принята!')}\n\n"
        f"👤 {hbold('Клиент:')} {client_name}\n"
        f"🎯 {hbold('Уровень:')} {level_names[level_key]}\n"
        f"⏰ {hbold('Время:')} {confirm_time} UTC\n"
        f"📝 {hbold('Задание:')}\n{task_text}"
    )

    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, admin_msg)
        except Exception as e:
            logging.error(f"Failed to notify admin {admin_id} about task acceptance: {e}")

    # Final message to client
    await callback.message.edit_text(
        f"✅ {hbold('Твой выбор принят!')}\n"
        f"Уровень: {hbold(level_names[level_key])}\n\n"
        f"🎯 {hbold('Задание:')}\n{task_text}\n\n"
        f"Действуй! Жду твой отчет вечером."
    )
    await callback.answer("Выбор подтвержден!")

@client_router.callback_query(F.data == "change_task_level")
async def task_level_change_request_handler(callback: types.CallbackQuery, bot: Bot):
    user = await FirestoreDB.get_user(callback.from_user.id)
    if not user: return
    
    from utils.gsheets_api import get_task_2_0
    from utils.timezone_utils import get_now_in_tz
    
    start_date = user.get('sprint_start_date') or user.get('created_at')
    if isinstance(start_date, str):
        try: start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        except: start_date = datetime.now(timezone.utc)
        
    day = (datetime.now(timezone.utc) - start_date).days + 1
    task_data = await get_task_2_0(day, user.get('scenario_type', 'Sovereign'))
    
    if not task_data:
        await callback.answer("Ошибка: данные задания не найдены.")
        return
        
    theory = task_data.get('theory', 'Пора приступать к работе.')
    day_name = task_data.get('day_name', f"День {day}")
    quality = user.get('target_quality_l1') or user.get('target_quality') or 'Проработка Тени'
    phase_text = f"{hitalic(task_data.get('phase'))}\n\n" if task_data.get('phase') else ""
    
    text = (
        f"💎 {hbold(quality)}: {day_name}\n\n"
        f"{phase_text}"
        f"{theory}\n\n"
        f"Выбери уровень сложности на сегодня:"
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text="◽️ Light", callback_data="task_level:light")
    builder.button(text="🔶 Medium", callback_data="task_level:medium")
    builder.button(text="🔥 Hard", callback_data="task_level:hard")
    builder.adjust(3)
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@client_router.callback_query(F.data == "confirm_log")
async def confirm_log_handler(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    content = data.get("temp_log_content")
    is_voice = data.get("is_voice", False)
    file_id = data.get("file_id")
    
    if not content:
        await callback.answer("Ошибка: данные отчета не найдены.")
        await state.clear()
        return

    user = await FirestoreDB.get_user(callback.from_user.id)
    if not user: return
    
    await process_shadow_log(callback.message, bot, user, content, is_voice, file_id)
    await state.clear()
    await callback.answer("Отправлено!")

@client_router.callback_query(F.data == "edit_log")
async def edit_log_handler(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_text("Хорошо, давай попробуем еще раз. 🎙\nПришли исправленное сообщение или запиши новое аудио.")
    # State remains or we can reset to waiting_for_log
    from bot.states import ClientStates
    await state.set_state(ClientStates.waiting_for_log)
