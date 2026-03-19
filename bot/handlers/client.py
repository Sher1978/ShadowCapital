from aiogram import Router, types, F, Bot
from aiogram.filters import CommandStart, Command
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

@client_router.message(F.text == "📝 Shadow Log")
async def shadow_log_prompt_handler(message: types.Message):
    """
    Prompt the user to send their daily log.
    """
    text = (
        f"{hbold('📝 Твой Shadow Log')}\n\n"
        "Это пространство для твоей честности. Расскажи, как прошел твой день в контексте Спринта:\n"
        "• Как проявилось твое новое качество?\n"
        "• Столкнулся ли ты с сопротивлением?\n"
        "• Какие инсайты или 'тени' ты заметил?\n\n"
        f"{hitalic('Пришли текстовое или голосовое сообщение прямо сейчас.')} Бот проанализирует его на предмет саботажа и даст обратную связь."
    )
    await message.answer(text)

@client_router.message(F.text | F.voice | F.audio)
async def log_handler(message: types.Message, bot: Bot):
    user = await FirestoreDB.get_user(message.from_user.id)
    
    if not user or user.get('role') != "client":
        return # Ignore non-clients or other messages

    is_voice = message.voice is not None or message.audio is not None
    file_id = None
    content = message.text
    
    if is_voice:
        # We have a voice/audio message
        file_id = message.voice.file_id if message.voice else message.audio.file_id
        await message.answer("🔊 Обрабатываю твое голосовое сообщение...")
        
        # Download file
        file = await bot.get_file(file_id)
        perm_path = f"media/audio/{file_id}.ogg"
        await bot.download_file(file.file_path, perm_path)
        
        # Transcribe
        transcript = await transcribe_voice(perm_path)
        content = transcript
    
    if not content:
        content = "Empty Log"

    # Analyze for sabotage
    analysis = await analyze_sabotage(
        content, 
        quality_name=user.get('target_quality_l1', "Unknown"),
        scenario_type=user.get('scenario_type', "N/A")
    )

    log_data = {
        "content": content,
        "is_voice": is_voice,
        "file_id": file_id,
        "local_file_path": f"media/audio/{file_id}.ogg" if is_voice else None,
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
