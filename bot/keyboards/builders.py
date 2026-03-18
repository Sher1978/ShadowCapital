from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_main_keyboard(is_admin: bool = False, is_active: bool = True):
    builder = ReplyKeyboardBuilder()
    
    if is_admin:
        # Admin-specific menu: Only management tools
        builder.button(text="👥 Клиенты")
        builder.button(text="⏳ Заявки")
        builder.button(text="📊 Аналитика")
        builder.button(text="➕ Добавить клиента")
        builder.button(text="⚙️ Настройки")
        builder.adjust(2, 2, 1)
        return builder.as_markup(resize_keyboard=True)

    # Client-specific menu
    if not is_active:
        builder.button(text="🚀 Активировать Спринт")
        builder.adjust(1)
        return builder.as_markup(resize_keyboard=True)

    builder.button(text="🎯 Моя цель")
    builder.button(text="📝 Shadow Log")
    builder.button(text="📈 Мои результаты")
    builder.button(text="🆘 SOS")
    builder.button(text="⚙️ Настройки")
    builder.button(text="Как это работает")
    
    builder.adjust(2, 2, 2)
    return builder.as_markup(resize_keyboard=True)
