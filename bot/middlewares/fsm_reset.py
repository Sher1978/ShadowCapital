from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

MENU_KEYWORDS = {
    "Моя цель", "Shadow Log", "SOS", "Настройки", 
    "Как это работает", "Клиенты", "Аналитика", "Заявки", 
    "Админ Панель", "Спринты", "Активировать Спринт", "Мои результаты",
    "Добавить клиента", "Назад", "Отмена", "Start", "Меню", "🏠 В меню"
}

import logging
logger = logging.getLogger(__name__)

class FsmResetMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any],
    ) -> Any:
        if isinstance(event, Message) and event.text:
            text = event.text
            # Robust check for menu buttons (any keyword present in text)
            # Use strip() and check if any keyword is a substring of the message text
            # We also strip emojis from the keywords if needed, but here we just check substring
            is_menu_button = any(keyword.strip() in text for keyword in MENU_KEYWORDS)
            is_command = text.startswith("/")
            
            if is_menu_button or is_command:
                state: FSMContext = data.get("state")
                if state:
                    current_state = await state.get_state()
                    if current_state:
                        logger.info(f"🔄 FSM Reset for user {event.from_user.id}: clearing state {current_state} on button '{text}'")
                        await state.clear()
                    else:
                        logger.debug(f"ℹ️ User {event.from_user.id} clicked '{text}', state already None")
                else:
                    logger.debug(f"ℹ️ No state object for user {event.from_user.id} on '{text}'")
            else:
                # Debug log to see why it didn't match
                logger.debug(f"ℹ️ Message '{text}' from {event.from_user.id} is not a menu button")
        
        return await handler(event, data)
