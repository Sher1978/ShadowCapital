from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.markdown import hbold, hitalic
from database.firebase_db import FirestoreDB
from bot.states import AuditStates
from datetime import datetime, timezone
import logging

audit_router = Router()

def get_1_10_keyboard(currency: str):
    builder = InlineKeyboardBuilder()
    for i in range(1, 11):
        builder.button(text=str(i), callback_data=f"audit_score:{currency}:{i}")
    builder.adjust(5)
    return builder.as_markup()

@audit_router.callback_query(F.data == "start_audit")
async def start_audit_handler(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(AuditStates.waiting_for_money)
    await callback.message.edit_text(
        f"🗝 {hbold('SHADOW CURRENCY AUDIT')}\n\n"
        "Мы начинаем замер твоих жизненных активов.\n\n"
        f"💰 1/4. {hbold('ДЕНЬГИ (MONEY)')}\n"
        "Насколько ты доволен своей финансовой реализацией и скоростью капитализации прямо сейчас? (1 - спячка, 10 - гиперпрыжок)",
        reply_markup=get_1_10_keyboard("money")
    )
    await callback.answer()

@audit_router.callback_query(AuditStates.waiting_for_money, F.data.startswith("audit_score:money:"))
async def audit_money_handler(callback: types.CallbackQuery, state: FSMContext):
    score = int(callback.data.split(":")[-1])
    await state.update_data(money=score)
    await state.set_state(AuditStates.waiting_for_time)
    await callback.message.edit_text(
        f"⏳ 2/4. {hbold('ВРЕМЯ (TIME)')}\n"
        "Насколько ты субъективно владеешь своим временем? (1 - хаос/рабство, 10 - абсолютный тайм-менеджмент и свобода)",
        reply_markup=get_1_10_keyboard("time")
    )
    await callback.answer()

@audit_router.callback_query(AuditStates.waiting_for_time, F.data.startswith("audit_score:time:"))
async def audit_time_handler(callback: types.CallbackQuery, state: FSMContext):
    score = int(callback.data.split(":")[-1])
    await state.update_data(time=score)
    await state.set_state(AuditStates.waiting_for_status)
    await callback.message.edit_text(
        f"👑 3/4. {hbold('СТАТУС (STATUS)')}\n"
        "Твой вес в социуме, проявленность и признание твоих границ. (1 - невидимость, 10 - неоспоримый авторитет)",
        reply_markup=get_1_10_keyboard("status")
    )
    await callback.answer()

@audit_router.callback_query(AuditStates.waiting_for_status, F.data.startswith("audit_score:status:"))
async def audit_status_handler(callback: types.CallbackQuery, state: FSMContext):
    score = int(callback.data.split(":")[-1])
    await state.update_data(status=score)
    await state.set_state(AuditStates.waiting_for_drive)
    await callback.message.edit_text(
        f"🔋 4/4. {hbold('ДРАЙВ / ЛИБИДО (DRIVE)')}\n"
        "Твой уровень энергии, жажды жизни и экспансии. (1 - выгорание, 10 - ядерный реактор)",
        reply_markup=get_1_10_keyboard("drive")
    )
    await callback.answer()

@audit_router.callback_query(AuditStates.waiting_for_drive, F.data.startswith("audit_score:drive:"))
async def audit_drive_handler(callback: types.CallbackQuery, state: FSMContext):
    score = int(callback.data.split(":")[-1])
    await state.update_data(drive=score)
    await state.set_state(AuditStates.waiting_for_focus)
    
    builder = InlineKeyboardBuilder()
    builder.button(text="💰 Money", callback_data="audit_focus:Money")
    builder.button(text="⏳ Time", callback_data="audit_focus:Time")
    builder.button(text="👑 Status", callback_data="audit_focus:Status")
    builder.button(text="🔋 Drive", callback_data="audit_focus:Drive")
    builder.adjust(2)
    
    await callback.message.edit_text(
        f"🎯 {hbold('ФОКУС НЕДЕЛИ')}\n\n"
        "Какая валюта сейчас является приоритетной для твоего роста? "
        "Где Тень тормозит тебя сильнее всего?",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@audit_router.callback_query(AuditStates.waiting_for_focus, F.data.startswith("audit_focus:"))
async def audit_finish_handler(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    focus = callback.data.split(":")[-1]
    data = await state.get_data()
    await state.clear()
    
    user = await FirestoreDB.get_user(callback.from_user.id)
    if not user: return

    # Calculate current day
    start_date = user.get('sprint_start_date') or user.get('created_at')
    if isinstance(start_date, (str, datetime)) is False: # Check if it is a Timestamp
         try: start_date = start_date.to_datetime()
         except: pass

    if isinstance(start_date, str):
        try: start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        except: start_date = datetime.now(timezone.utc)
    
    day_number = (datetime.now(timezone.utc) - start_date).days + 1
    
    audit_results = {
        "money": data.get('money', 0),
        "time": data.get('time', 0),
        "status": data.get('status', 0),
        "drive": data.get('drive', 0),
        "focus_currency": focus
    }
    
    # Save to user audits collection
    await FirestoreDB.save_audit(user['id'], day_number, audit_results)
    # Update main user document for AI context
    await FirestoreDB.update_user(user['id'], {"focus_currency": focus})
    
    # Sync to GSheets
    from utils.gsheets_api import sync_user_to_sheets
    try:
        await sync_user_to_sheets(user['id'], {"focus_currency": focus})
    except Exception as e:
        logging.error(f"Failed to sync focus to sheets: {e}")
    
    # Send user summary
    await callback.message.edit_text(
        f"✅ {hbold('АУДИТ ЗАВЕРШЕН')}\n\n"
        f"Твое текущее состояние зафиксировано в Human OS.\n"
        f"Фокус недели: {hbold(focus)}\n\n"
        "Ты разблокировал доступ к сегодняшнему импульсу. Сейчас я пришлю задание."
    )
    
    # Trigger task delivery (to prevent "locking" the user out)
    from utils.scheduler import send_morning_impulse
    # We call it manually for this specific user
    try:
        await send_morning_impulse(bot, user, bypass_audit=True)
    except Exception as e:
        logging.error(f"Failed to auto-trigger task after audit: {e}")
    
    # Notify Admin
    from utils.alerts import send_audit_report
    try:
        await send_audit_report(bot, user, audit_results, day_number)
    except Exception as e:
        logging.error(f"Failed to send audit report to admin: {e}")

    await callback.answer()
