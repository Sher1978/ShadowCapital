from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

MENU_BUTTONS = {
    "🎯 Моя цель", "📝 Shadow Log", "🆘 SOS", "⚙️ Настройки", 
    "Как это работает", "👥 Клиенты", "📊 Аналитика", "⏳ Заявки", 
    "💼 Админ Панель", "🚀 Спринты", "🚀 Активировать Спринт", "📈 Мои результаты",
    "➕ Добавить клиента"
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
        if isinstance(event, Message) and event.text in MENU_BUTTONS:
            state: FSMContext = data.get("state")
            if state:
                current_state = await state.get_state()
                if current_state:
                    await state.clear()
        return await handler(event, data)
