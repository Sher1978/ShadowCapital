from aiogram import Router, types, F, Bot
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.markdown import hbold, hitalic
from database.firebase_db import FirestoreDB
from bot.keyboards.builders import get_main_keyboard
import os
import logging
from utils.transcription import transcribe_voice
from utils.analysis import analyze_sabotage
from utils.alerts import send_red_alert
from utils.gsheets_api import sync_user_to_sheets
from config import ADMIN_IDS
from datetime import datetime, timezone

client_router = Router()

@client_router.message(F.text == "🏠 В меню")
async def client_back_to_menu(message: types.Message):
    await message.answer("Возврат в меню.", reply_markup=get_main_keyboard(is_admin=False))

@client_router.message(CommandStart())
async def command_start_handler(message: types.Message) -> None:
    is_admin = message.from_user.id in ADMIN_IDS
    
    user = await FirestoreDB.get_user(message.from_user.id)
    
    if not user:
        user_data = {
            "tg_id": message.from_user.id,
            "username": message.from_user.username,
            "full_name": message.from_user.full_name,
            "role": "admin" if is_admin else "client",
            "status": "active" if is_admin else "new",
            "sfi_index": 1.0,
            "red_flags_count": 0
        }
        doc_id = await FirestoreDB.create_user(user_data)
        user = user_data
        user['id'] = doc_id
        
    is_active = (user.get('status') == "active") or is_admin
    
    await message.answer(
        f"Привет, {hbold(message.from_user.full_name)}! Бот Shadow Guardian на связи.\n"
        f"Если ты участник Shadow Sprint, я буду сопровождать тебя ближайшие 30 дней.",
        reply_markup=get_main_keyboard(is_admin, is_active=is_active)
    )

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

    # Notify Admins
    from aiogram import Bot
    bot = callback.bot
    client_name = user.get('full_name', "N/A")
    confirm_time = datetime.now(timezone.utc).strftime("%H:%M")
    
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

@client_router.message(F.text == "Как это работает")
async def how_it_works_handler(message: types.Message) -> None:
    text = (
        f"{hbold('Как проходит Shadow Sprint:')}\n\n"
        f"1. {hbold('Утренний Импульс (09:00):')} Ты получаешь задание на день. Это микро-действие для интеграции твоего нового качества.\n"
        f"2. {hbold('Вечерний Shadow Log (20:00):')} Ты присылаешь отчет (текст или голос). Рассказываешь, как проявилось качество и какое было сопротивление.\n"
        f"3. {hbold('Обход Хранителя:')} Мы действуем незаметно, чтобы твоя психика не блокировала изменения.\n\n"
        f"Твоя задача — быть честным в отчетах. ИИ проанализирует их и даст сигнал куратору, если заметит саботаж."
    )
    await message.answer(text)

@client_router.message(F.text == "Моя цель")
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

@client_router.message(F.text == "🆘 SOS")
async def sos_handler(message: types.Message, bot: Bot):
    user = await FirestoreDB.get_user(message.from_user.id)
    
    if not user:
        return

    await send_red_alert(
        bot,
        user.get('full_name', "Клиент"),
        user.get('tg_id'),
        "SOS",
        "Запрос экстренной связи от клиента",
        "Нажата кнопка SOS в боте."
    )
        
    await message.answer(
        "🆘 Сигнал SOS отправлен куратору. Тебя 'накрыло' сопротивление? \n\n"
        "Не переживай, это нормально. Куратор свяжется с тобой в ближайшее время. "
        "Попробуй пока просто дышать и наблюдать за этим чувством."
    )

@client_router.message(Command("wipe_data"))
async def delete_my_data_handler(message: types.Message):
    """
    Deletes all user logs (GDPR-like compliance).
    """
    async with get_db_session() as session:
        stmt_user = select(User).where(User.tg_id == message.from_user.id)
        result = await session.execute(stmt_user)
        user = result.scalar_one_or_none()
        
        if not user:
            return

        # Delete all logs
        await session.execute(delete(ShadowLog).where(ShadowLog.user_id == user.id))
        await session.commit()
    
    await message.answer(
        "🗑 Все твои Shadow Logs были безвозвратно удалены из системы. \n"
        "Мы ценим твою приватность. Твой прогресс (качество) сохранен, "
        "но история сообщений очищена."
    )

async def trigger_shadow_log_prompt(message: types.Message):
    """Refactored helper to show the report prompt."""
    text = (
        f"{hbold('📝 Твой Shadow Log')}\n\n"
        "Это пространство для твоей честности. Расскажи, как прошел твой день в контексте Спринта:\n"
        "• Как проявилось твое новое качество?\n"
        "• Столкнулся ли ты с сопротивлением?\n"
        "• Какие инсайты или 'тени' ты заметил?\n\n"
        f"{hitalic('Пришли текстовое или голосовое сообщение прямо сейчас.')} Бот проанализирует его на предмет саботажа и даст обратную связь."
    )
    from aiogram.utils.keyboard import ReplyKeyboardBuilder
    builder = ReplyKeyboardBuilder()
    builder.button(text="🏠 В меню")
    await message.answer(text, reply_markup=builder.as_markup(resize_keyboard=True))

@client_router.message(F.text == "📝 Shadow Log")
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
    # Simple menu return - user is active if they are here
    await callback.message.answer("Возврат в меню.", reply_markup=get_main_keyboard(is_admin=False, is_active=True))
    await callback.answer()

@client_router.callback_query(F.data == "re_submit_log")
async def re_submit_log_callback(callback: types.CallbackQuery):
    await callback.message.edit_reply_markup(reply_markup=None)
    await trigger_shadow_log_prompt(callback.message)
    await callback.answer()

@client_router.message(F.text | F.voice | F.audio)
async def log_handler(message: types.Message, bot: Bot, state: FSMContext):
    user = await FirestoreDB.get_user(message.from_user.id)
    
    if not user:
        return # Ignore unknown users
        
    # Allow admins to test logs, or just clients
    if user.get('role') not in ["client", "admin"]:
        return

    is_voice = message.voice is not None or message.audio is not None
    file_id = None
    content = message.text
    
    if is_voice:
        try:
            # We have a voice/audio message
            file_id = message.voice.file_id if message.voice else message.audio.file_id
            await message.answer("🔊 Обрабатываю твое голосовое сообщение...")
            
            # Download file to /tmp (Cloud Run only allows writes to /tmp)
            import tempfile
            temp_dir = tempfile.gettempdir()
            perm_path = os.path.join(temp_dir, f"{file_id}.ogg")
            
            file = await bot.get_file(file_id)
            await bot.download_file(file.file_path, perm_path)
            
            # Transcribe
            content = await transcribe_voice(perm_path)
            
            # Cleanup
            if os.path.exists(perm_path):
                os.remove(perm_path)
            
            # Transcription Confirmation UI
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

    # Analyze for sabotage
    from utils.analysis import analyze_sabotage
    analysis = await analyze_sabotage(
        content, 
        quality_name=user.get('target_quality_l1', "Unknown"),
        scenario_type=user.get('scenario_type', "N/A")
    )

    log_data = {
        "content": content,
        "is_voice": is_voice,
        "file_id": file_id,
        "local_file_path": None,
        "is_sabotage": analysis.get("is_sabotage", False),
        "sfi_score": analysis.get("sfi_score", 0.5),
        "feedback_to_client": analysis.get("feedback_to_client", ""),
        "analysis_reason": analysis.get("internal_analysis", "")
    }
    await FirestoreDB.add_log(user['id'], log_data)
    
    # Update User Dashboard Stats
    update_data = {
        "sfi_index": analysis.get("sfi_score", 0.5),
        "last_insight": analysis.get("last_insight", "")
    }
    
    # Red Flag Logic
    if analysis.get("is_sabotage", False):
        red_flags = user.get('red_flags_count', 0) + 1
        update_data["red_flags_count"] = red_flags
        
        if red_flags >= 3:
            # Notify admin about critical sabotage level
            for admin_id in ADMIN_IDS:
                try:
                    await bot.send_message(
                        admin_id, 
                        f"🚨 {hbold('CRITICAL RED ALERT')}: Клиент {user.get('full_name')} ({user.get('tg_id')}) набрал {red_flags} флагов саботажа!\n"
                        f"Требуется прямое вмешательство."
                    )
                except: pass
        
        # Send Red Alert to Admin
        await send_red_alert(
            bot, 
            user.get('full_name'), 
            user.get('tg_id'), 
            "SABOTAGE", 
            analysis.get("internal_analysis", "N/A"),
            content
        )
    
    await FirestoreDB.update_user(user['id'], update_data)

    # Sync update to Google Sheets
    await sync_user_to_sheets({
        "user_id": user.get('tg_id'),
        "name": user.get('full_name'),
        "target_quality": user.get('target_quality_l1'),
        "scenario": user.get('scenario_type'),
        "red_flags": update_data.get("red_flags_count", user.get('red_flags_count', 0)),
        "sfi_index": update_data["sfi_index"],
        "last_insight": update_data["last_insight"]
    })
        
    # Send AI auditor feedback back to user
    feedback = analysis.get("feedback_to_client") or "Принято, твой Shadow Log сохранен."
    await message.answer(feedback)

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

    await callback.message.edit_text("⌛️ Анализирую твой отчет...")
    
    # We call the core log processing logic. 
    # To avoid duplication, we could refactor log_handler to a shared function.
    # For now, I'll extract it or just repeat since it's short.
    
    user = await FirestoreDB.get_user(callback.from_user.id)
    if not user: return
    
    # --- CORE ANALYSIS LOGIC ---
    from utils.analysis import analyze_sabotage
    analysis = await analyze_sabotage(
        content, 
        quality_name=user.get('target_quality_l1', "Unknown"),
        scenario_type=user.get('scenario_type', "N/A")
    )

    log_data = {
        "content": content,
        "is_voice": is_voice,
        "file_id": file_id,
        "local_file_path": None,
        "is_sabotage": analysis.get("is_sabotage", False),
        "sfi_score": analysis.get("sfi_score", 0.5),
        "feedback_to_client": analysis.get("feedback_to_client", ""),
        "analysis_reason": analysis.get("internal_analysis", "")
    }
    await FirestoreDB.add_log(user['id'], log_data)
    
    update_data = {
        "sfi_index": analysis.get("sfi_score", 0.5),
        "last_insight": analysis.get("last_insight", "")
    }
    
    if analysis.get("is_sabotage", False):
        red_flags = user.get('red_flags_count', 0) + 1
        update_data["red_flags_count"] = red_flags
        
        for admin_id in ADMIN_IDS:
             try:
                 if red_flags >= 3:
                     await bot.send_message(admin_id, f"🚨 {hbold('CRITICAL RED ALERT')}: {user.get('full_name')} ({user.get('tg_id')}) [{red_flags}/3]")
                 await send_red_alert(bot, user.get('full_name'), user.get('tg_id'), "SABOTAGE", analysis.get("internal_analysis", ""), content)
             except: pass

    await FirestoreDB.update_user(user['id'], update_data)
    
    await sync_user_to_sheets({
        "user_id": user.get('tg_id'),
        "name": user.get('full_name'),
        "target_quality": user.get('target_quality_l1'),
        "scenario": user.get('scenario_type'),
        "red_flags": update_data.get("red_flags_count", user.get('red_flags_count', 0)),
        "sfi_index": update_data["sfi_index"],
        "last_insight": update_data["last_insight"]
    })
    
    feedback = analysis.get("feedback_to_client") or "Принято, твой Shadow Log сохранен."
    await callback.message.answer(feedback)
    await state.clear()
    await callback.answer("Отправлено!")

@client_router.callback_query(F.data == "edit_log")
async def edit_log_handler(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_text("Хорошо, давай попробуем еще раз. 🎙\nПришли исправленное сообщение или запиши новое аудио.")
    # State remains or we can reset to waiting_for_log
    from bot.states import ClientStates
    await state.set_state(ClientStates.waiting_for_log)
