from aiogram import Router, types, F, Bot
from aiogram.filters import CommandStart, Command
from aiogram.utils.markdown import hbold, hitalic
from database.connection import get_db_session
from database.models import User, ShadowMap, ShadowLog
from sqlalchemy import select, delete
from sqlalchemy.orm import joinedload
from bot.keyboards.builders import get_main_keyboard
import os
import logging
from utils.transcription import transcribe_voice
from utils.analysis import analyze_sabotage
from utils.alerts import send_red_alert
from utils.gsheets_api import sync_user_to_sheets
from config import ADMIN_IDS
from datetime import datetime

client_router = Router()

@client_router.message(CommandStart())
async def command_start_handler(message: types.Message) -> None:
    is_admin = message.from_user.id in ADMIN_IDS
    
    async with get_db_session() as session:
        stmt = select(User).where(User.tg_id == message.from_user.id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            user = User(
                tg_id=message.from_user.id,
                username=message.from_user.username,
                full_name=message.from_user.full_name,
                role="admin" if is_admin else "client",
                status="active" if is_admin else "new"
            )
            session.add(user)
            await session.commit()
            
        is_active = (user.status == "active") or is_admin
        
        await message.answer(
            f"Привет, {hbold(message.from_user.full_name)}! Бот Shadow Guardian на связи.\n"
            f"Если ты участник Shadow Sprint, я буду сопровождать тебя ближайшие 30 дней.",
            reply_markup=get_main_keyboard(is_admin, is_active=is_active)
        )

@client_router.message(F.text == "🚀 Активировать Спринт")
async def activate_request_handler(message: types.Message):
    async with get_db_session() as session:
        stmt = select(User).where(User.tg_id == message.from_user.id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user or user.status == "active" or user.status == "pending":
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
    async with get_db_session() as session:
        stmt = select(User).where(User.tg_id == callback.from_user.id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user or user.status == "active" or user.status == "pending":
            await callback.answer("Твой статус уже обновлен.")
            return

        user.rules_accepted = True
        user.rules_accepted_at = datetime.now()
        user.status = "pending"
        await session.commit()
        
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
    async with get_db_session() as session:
        stmt = select(User).where(User.tg_id == message.from_user.id).options(joinedload(User.shadow_map))
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user or not user.shadow_map:
            await message.answer("Твой Shadow Sprint еще не активирован. Ожидай регистрации куратором.")
            return
            
        text = (
            f"Твоя текущая цель:\n\n"
            f"🎯 {hbold('Качество:')} {user.shadow_map.quality_name}\n"
            f"✨ {hbold('Золотой потенциал:')}\n{hitalic(user.shadow_map.potential_desc)}"
        )
        await message.answer(text)

@client_router.message(F.text == "🆘 SOS")
async def sos_handler(message: types.Message, bot: Bot):
    async with get_db_session() as session:
        stmt = select(User).where(User.tg_id == message.from_user.id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            return

        await send_red_alert(
            bot,
            user.full_name or "Клиент",
            user.tg_id,
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

@client_router.message(F.text | F.voice | F.audio)
async def log_handler(message: types.Message, bot: Bot):
    async with get_db_session() as session:
        # Check if user is a client
        stmt = select(User).where(User.tg_id == message.from_user.id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user or user.role != "client":
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
            # Note: We keep the file in /media/audio/ permanently now.
        
        if not content:
            content = "Empty Log"

        # Analyze for sabotage
        analysis = await analyze_sabotage(
            content, 
            quality_name=user.target_quality_l1 or "Unknown",
            scenario_type=user.scenario_type or "N/A"
        )

        new_log = ShadowLog(
            user_id=user.id,
            content=content,
            is_voice=is_voice,
            file_id=file_id,
            local_file_path=f"media/audio/{file_id}.ogg" if is_voice else None,
            is_sabotage=analysis.get("is_sabotage", False),
            sfi_score=analysis.get("sfi_score", 0.5),
            feedback_to_client=analysis.get("feedback_to_client", ""),
            analysis_reason=analysis.get("internal_analysis", "")
        )
        session.add(new_log)
        
        # Update User Dashboard Stats
        user.sfi_index = analysis.get("sfi_score", 0.5)
        user.last_insight = analysis.get("last_insight", "")
        
        # Red Flag Logic
        if analysis.get("is_sabotage", False):
            user.red_flags_count = (user.red_flags_count or 0) + 1
            if user.red_flags_count >= 3:
                # Notify admin about critical sabotage level
                for admin_id in ADMIN_IDS:
                    try:
                        await bot.send_message(
                            admin_id, 
                            f"🚨 {hbold('CRITICAL RED ALERT')}: Клиент {user.full_name} ({user.tg_id}) набрал {user.red_flags_count} флагов саботажа!\n"
                            f"Требуется прямое вмешательство."
                        )
                    except: pass
            
            # Send Red Alert to Admin
            await send_red_alert(
                bot, 
                user.full_name, 
                user.tg_id, 
                "SABOTAGE", 
                analysis.get("internal_analysis", "N/A"),
                content
            )
        
        await session.commit()

        # Sync update to Google Sheets
        await sync_user_to_sheets({
            "user_id": user.tg_id,
            "name": user.full_name,
            "target_quality": user.target_quality_l1,
            "scenario": user.scenario_type,
            "red_flags": user.red_flags_count,
            "sfi_index": user.sfi_index,
            "last_insight": user.last_insight
        })
        
    # Send AI auditor feedback back to user
    feedback = analysis.get("feedback_to_client") or "Принято, твой Shadow Log сохранен."
    await message.answer(feedback)
