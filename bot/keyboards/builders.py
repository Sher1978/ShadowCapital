from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_main_keyboard(is_admin: bool = False, is_active: bool = True):
    builder = ReplyKeyboardBuilder()
    
    if is_admin:
        # Admin-specific menu: Only management tools
        builder.button(text="👥 Клиенты")
        builder.button(text="⌛️ Заявки")
        builder.button(text="📁 Архив")
        builder.button(text="📊 Аналитика")
        builder.button(text="➕ Добавить клиента")
        builder.button(text="⚙️ Настройки")
        builder.adjust(2, 2, 2)
        return builder.as_markup(resize_keyboard=True)

    # Client-specific menu
    if not is_active:
        builder.button(text="🚀 Активировать Спринт")
        builder.adjust(1)
        return builder.as_markup(resize_keyboard=True)

    builder.button(text="🎯 Моя цель")
    builder.button(text="📝 Вечерний Отчет")
    builder.button(text="📈 Мои результаты")
    builder.button(text="❓ Вопрос куратору")
    builder.button(text="⚙️ Настройки")
    builder.button(text="📖 Инструкция")
    
    builder.adjust(2, 2, 2)
    return builder.as_markup(resize_keyboard=True)

def get_navigation_keyboard(is_admin: bool = False, back_callback: str = None):
    """
    Returns a ReplyKeyboardMarkup with 'Back' and 'To Menu' buttons.
    """
    builder = ReplyKeyboardBuilder()
    builder.button(text="⬅️ Назад")
    builder.button(text="🏠 В меню")
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def get_inline_back_button(callback_data: str):
    """
    Returns an InlineKeyboardMarkup with a single 'Back' button.
    """
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Назад", callback_data=callback_data)
    return builder.as_markup()

def get_day_change_action_keyboard(client_id: str):
    """
    Returns an InlineKeyboardMarkup with choices for what to send after a day change.
    """
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text="☀️ Утренний Импульс", callback_data=f"send_now_morning_{client_id}")
    builder.button(text="🌙 Вечерний Отчет", callback_data=f"send_now_evening_{client_id}")
    builder.button(text="🏠 В меню", callback_data="back_to_main_menu")
    builder.adjust(1)
    return builder.as_markup()
