from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

MENU_KEYWORDS = {
    "Моя цель", "Shadow Log", "SOS", "Настройки", 
    "Как это работает", "Клиенты", "Аналитика", "Заявки", 
    "Админ Панель", "Спринты", "Активировать Спринт", "Мои результаты",
    "Добавить клиента", "Назад", "Отмена", "Start", "Меню"
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
            is_menu_button = any(keyword in text for keyword in MENU_KEYWORDS)
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
        
        return await handler(event, data)
