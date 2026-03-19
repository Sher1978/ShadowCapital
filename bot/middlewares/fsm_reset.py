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

class FsmResetMiddleware(BaseMiddleware):
    """
    Clears FSM state if a user clicks a main menu button.
    This prevents the bot from being 'stuck' in an input scenario.
    """
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any],
    ) -> Any:
        if isinstance(event, Message) and event.text:
            # Robust check for menu buttons (any keyword present in text)
            is_menu_button = any(keyword in event.text for keyword in MENU_KEYWORDS)
            is_command = event.text.startswith("/")
            
            if is_menu_button or is_command:
                state: FSMContext = data.get("state")
                if state:
                    current_state = await state.get_state()
                    if current_state:
                        await state.clear()
        
        return await handler(event, data)
