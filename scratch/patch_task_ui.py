import os
import codecs

def patch_file(file_path, search_pattern, replacement_text, is_multiline=False):
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found")
        return False
    
    with codecs.open(file_path, 'r', 'utf-8') as f:
        content = f.read()
    
    if search_pattern not in content:
        print(f"Error: Pattern not found in {file_path}")
        # Try without some whitespace if it's a code block
        return False
    
    new_content = content.replace(search_pattern, replacement_text)
    
    with codecs.open(file_path, 'w', 'utf-8') as f:
        f.write(new_content)
    print(f"Successfully patched {file_path}")
    return True

# --- Patch builders.py ---
builders_path = r'c:\Sher_AI_Studio\projects\Shadow_Corp\Sprint_bot\bot\keyboards\builders.py'

# Add "🎯 Задание" button
search_builders = '    builder.button(text="🎯 Моя цель")\r\n    builder.button(text="📝 Вечерний Отчет")'
# Try with different line endings just in case
if search_builders not in codecs.open(builders_path, 'r', 'utf-8').read():
    search_builders = '    builder.button(text="🎯 Моя цель")\n    builder.button(text="📝 Вечерний Отчет")'

replace_builders = '    builder.button(text="🎯 Моя цель")\n    builder.button(text="🎯 Задание")\n    builder.button(text="📝 Вечерний Отчет")'

patch_file(builders_path, search_builders, replace_builders)


# --- Patch client.py ---
client_path = r'c:\Sher_AI_Studio\projects\Shadow_Corp\Sprint_bot\bot\handlers\client.py'

# 1. Add manual_task_trigger (near instruction_handler or after my_goal_handler)
search_client_handler = '@client_router.message(F.text == "🎯 Моя цель")\nasync def my_goal_handler(message: types.Message) -> None:'
if search_client_handler not in codecs.open(client_path, 'r', 'utf-8').read():
    search_client_handler = '@client_router.message(F.text == "🎯 Моя цель")\r\nasync def my_goal_handler(message: types.Message) -> None:'

replace_client_handler = """@client_router.message(F.text == "🎯 Задание")
async def manual_task_trigger(message: types.Message, state: FSMContext, bot: Bot):
    user = await FirestoreDB.get_user(message.from_user.id)
    if not user: return
    
    # Check if user is active
    if user.get('status') != "active" and message.from_user.id not in ADMIN_IDS:
        await message.answer("Для получения заданий твой профиль должен быть активирован.")
        return

    # Trigger task selection
    from .client import task_level_change_request_handler
    # Create a fake callback object to reuse the logic
    class FakeCallback:
        def __init__(self, message, user):
            self.message = message
            self.from_user = user
            self.bot = message.bot
        async def answer(self, text=None): pass

    await task_level_change_request_handler(FakeCallback(message, message.from_user), bot)

""" + search_client_handler

patch_file(client_path, search_client_handler, replace_client_handler)

# 2. Fix task_level_selection_handler logic and add confirmation
# Find the start of the handler to add the new confirm handler before it, or just append it.
# We'll replace the existing task_level_selection_handler entirely for safety.

search_selection_handler = """@client_router.callback_query(F.data.startswith("task_level:"))
async def task_level_selection_handler(callback: types.CallbackQuery, state: FSMContext, bot: Bot):"""

# Since it's a large block, I'll search for the specific broken part first
broken_end = """    is_admin = callback.from_user.id in ADMIN_IDS
    await callback.message.edit_text(
        full_task_msg, 
        reply_markup=get_main_keyboard(is_admin=is_admin, is_active=True)
    )
    await callback.answer()"""

# Normalizing whitespace for search
if broken_end not in codecs.open(client_path, 'r', 'utf-8').read():
    broken_end = broken_end.replace('\n', '\r\n')

fixed_end = """    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Принять и начать", callback_data=f"confirm_task:{level_str}")
    builder.button(text="⬅️ Изменить уровень", callback_data="change_task_level")
    builder.adjust(1)
    
    await callback.message.edit_text(
        full_task_msg, 
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@client_router.callback_query(F.data.startswith("confirm_task:"))
async def confirm_task_handler(callback: types.CallbackQuery, bot: Bot):
    level_str = callback.data.split(":")[1]
    level_names = {"light": "Light", "medium": "Medium", "hard": "Hard"}
    
    # Notify Admin
    user = await FirestoreDB.get_user(callback.from_user.id)
    if not user: return
    
    confirm_time = datetime.now(timezone.utc).strftime("%H:%M")
    
    admin_msg = (
        f"✅ {hbold('Задача принята!')}\\n\\n"
        f"👤 {hbold('Клиент:')} {user.get('full_name')}\\n"
        f"🎯 {hbold('Уровень:')} {level_names.get(level_str, level_str)}\\n"
        f"⏰ {hbold('Время:')} {confirm_time} UTC"
    )

    for admin_id in ADMIN_IDS:
        try: await bot.send_message(admin_id, admin_msg)
        except: pass

    await callback.message.edit_text(
        f"✅ {hbold('Твой выбор принят!')}\\n"
        f"Уровень: {hbold(level_names.get(level_str, level_str))}\\n\\n"
        f"Действуй! Жду твой отчет вечером.",
        reply_markup=None
    )
    
    # Re-send main menu to ensure access to other features
    is_admin_user = callback.from_user.id in ADMIN_IDS
    await callback.message.answer(
        "Используй меню ниже для навигации.", 
        reply_markup=get_main_keyboard(is_admin=is_admin_user, is_active=True)
    )
    await callback.answer("Задание принято!")"""

patch_file(client_path, broken_end, fixed_end)
