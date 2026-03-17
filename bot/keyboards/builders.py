from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_main_keyboard(is_admin: bool = False, is_active: bool = True):
    builder = ReplyKeyboardBuilder()
    
    if not is_active:
        builder.button(text="🚀 Активировать Спринт")
        builder.adjust(1)
        return builder.as_markup(resize_keyboard=True)

    builder.button(text="🎯 Моя цель")
    builder.button(text="📝 Shadow Log")
    builder.button(text="🆘 SOS")
    builder.button(text="⚙️ Настройки")
    builder.button(text="Как это работает")
    
    if is_admin:
        builder.row(KeyboardButton(text="👥 Клиенты"), KeyboardButton(text="📊 Аналитика"))
        builder.row(KeyboardButton(text="⚙️ Настройки"))
    else:
        builder.button(text="💼 Админ Панель")
    
    builder.adjust(2, 2, 2, 1)
    return builder.as_markup(resize_keyboard=True)
