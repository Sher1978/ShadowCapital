import asyncio
import logging
from aiogram import Router, types, F, Bot
from aiogram.filters import CommandStart, Command, StateFilter, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.utils.markdown import hbold, hitalic, hcode
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from bot.states import InitiationStates
from database.firebase_db import FirestoreDB
from config import ADMIN_IDS
from utils.initiation_constants import (
    VIDEO_VERDICT, VIDEO_CURRENCY, VERDICT_TEXTS, 
    ROI_MAP, CURRENCY_BLOW, FINAL_OFFER_TEXT
)

initiation_router = Router()

async def notify_admin_initiation(bot: Bot, user: dict, data: dict):
    """Notify admins about a new completed initiation funnel."""
    username = user.get('username') or "N/A"
    tg_id = user.get('tg_id')
    
    msg = (
        f"🔥 {hbold('НОВАЯ ЗАЯВКА НА АКТИВАЦИЮ!')}\n\n"
        f"👤 {hbold('Юзер:')} @{username} ({hcode(tg_id)})\n"
        f"🎬 {hbold('Сценарий:')} {data.get('scenario')}\n"
        f"💎 {hbold('Главный приоритет:')} {data.get('currency_label')}\n"
        f"🚀 {hbold('Действие:')} {data.get('action_answer')}\n"
        f"👥 {hbold('Окружение:')} {data.get('env_answer')}"
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text="👤 Профиль клиента", url=f"tg://user?id={tg_id}")
    
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, msg, reply_markup=builder.as_markup())
        except Exception as e:
            logging.error(f"Failed to notify admin {admin_id}: {e}")

async def start_shadow_initiation(message: types.Message, state: FSMContext, scenario: str):
    """Entry point for the funnel."""
    await state.clear()
    await state.update_data(scenario=scenario)
    
    # Step 1: Verdict Text + Video Round #1
    verdict_text = VERDICT_TEXTS.get(scenario, "Ваш вердикт подготавливается...")
    video_id = VIDEO_VERDICT.get(scenario)
    
    # Send video if available, otherwise just text
    if video_id and "Placeholder" not in video_id:
        try:
            await message.answer_video_note(video_id)
        except Exception as e:
            logging.warning(f"Could not send video_note {video_id}: {e}")
            await message.answer(f"🎥 {hitalic('[Видео-кружок Вердикта]')}")
    else:
        await message.answer(f"🎥 {hitalic('[Видео-кружок Вердикта]')}")
        
    await message.answer(verdict_text)
    
    # Step 2: ROI Table after 3 seconds
    await asyncio.sleep(3)
    await message.answer(ROI_MAP)
    
    # Step 3: Question 1
    await asyncio.sleep(1)
    await message.answer(
        "1/3. Представь, что через 30 дней этот баг исчез. Какое ОДНО действие ты совершишь первым делом, "
        "на которое сейчас тебе не хватает духу?"
    )
    await state.set_state(InitiationStates.waiting_for_action)

@initiation_router.message(InitiationStates.waiting_for_action)
async def process_action_step(message: types.Message, state: FSMContext):
    await state.update_data(action_answer=message.text)
    
    await message.answer(
        "2/3. Кто в твоем окружении первым заметит, что ты изменился, и как изменится их отношение к тебе?"
    )
    await state.set_state(InitiationStates.waiting_for_environment)

@initiation_router.message(InitiationStates.waiting_for_environment)
async def process_environment_step(message: types.Message, state: FSMContext):
    await state.update_data(env_answer=message.text)
    
    builder = InlineKeyboardBuilder()
    builder.button(text="💰 Деньги", callback_data="init_curr:money")
    builder.button(text="⏳ Время", callback_data="init_curr:time")
    builder.button(text="👑 Статус", callback_data="init_curr:status")
    builder.button(text="🔥 Либидо", callback_data="init_curr:libido")
    builder.adjust(2)
    
    await message.answer(
        "3/3. Чтобы сорвать этот \"ручник\" и забрать результат из таблицы выше — "
        "какая валюта тебе нужнее всего прямо сейчас?",
        reply_markup=builder.as_markup()
    )
    await state.set_state(InitiationStates.waiting_for_currency)

@initiation_router.callback_query(F.data.startswith("init_curr:"), InitiationStates.waiting_for_currency)
async def process_currency_choice(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    currency = callback.data.split(":")[1]
    currency_labels = {
        "money": "💰 Деньги",
        "time": "⏳ Время",
        "status": "👑 Статус",
        "libido": "🔥 Либидо"
    }
    label = currency_labels.get(currency, currency)
    await state.update_data(currency_choice=currency, currency_label=label)
    
    await callback.message.edit_reply_markup(reply_markup=None) # Remove buttons
    
    # Step 4: The Second Blow (Video #2)
    video_id = VIDEO_CURRENCY.get(currency)
    blow_text = CURRENCY_BLOW.get(currency, "")
    
    if video_id and "Placeholder" not in video_id:
        try:
            await bot.send_video_note(callback.from_user.id, video_id)
        except Exception as e:
            logging.warning(f"Could not send video_note {video_id}: {e}")
            await callback.message.answer(f"🎥 {hitalic('[Видео-кружок Валюты]')}")
    else:
        await callback.message.answer(f"🎥 {hitalic('[Видео-кружок Валюты]')}")
        
    await callback.message.answer(f"«{hbold(label)} — это правильный выбор.»\n\n{blow_text}")
    
    # Step 5: Final CTA
    await asyncio.sleep(2)
    
    builder = InlineKeyboardBuilder()
    builder.button(text="⚡️ Записаться на Активацию к Шеру", callback_data="initiation_finish")
    
    await callback.message.answer(FINAL_OFFER_TEXT, reply_markup=builder.as_markup())
    await callback.answer()

@initiation_router.callback_query(F.data == "initiation_finish")
async def finish_initiation(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    user = await FirestoreDB.get_user(callback.from_user.id)
    
    if not user:
        # Create user if doesn't exist (though they should)
        user = {
            "tg_id": callback.from_user.id,
            "username": callback.from_user.username,
            "full_name": callback.from_user.full_name
        }
        await FirestoreDB.create_user(user)

    # Save to Firestore
    await FirestoreDB.update_user(user['id'], {
        "initiation_data": data,
        "initiation_completed_at": FirestoreDB.now_utc(),
        "status": "initiation_completed"
    })
    
    # Notify Admin
    await notify_admin_initiation(bot, user, data)
    
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("✅ Ваша заявка отправлена. Шер свяжется с вами в ближайшее время.")
    await callback.answer("Заявка отправлена!")
    await state.clear()

@initiation_router.message(CommandStart(deep_link=True))
async def initiation_deeplink_handler(message: types.Message, command: CommandObject, state: FSMContext):
    """Prioritized handler for SFI deeplinks."""
    args = command.args
    if args and args.startswith("sfi_"):
        scenario = args.split("_")[1].upper()
        if scenario in ["A", "B", "C", "D"]:
            await start_shadow_initiation(message, state, scenario)
            return
    
    # If it's a deeplink but not sfi_, we let it fall through to other routers
    return
