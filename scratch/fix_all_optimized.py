import os
import codecs

def patch_file(file_path, patch_id, search_pattern, replacement_text):
    if not os.path.exists(file_path):
        print(f"[{patch_id}] Error: {file_path} not found")
        return False
    
    with codecs.open(file_path, 'r', 'utf-8') as f:
        content = f.read()
    
    # Normalize line endings for searching
    search_n = search_pattern.replace('\r\n', '\n')
    search_rn = search_pattern.replace('\n', '\r\n')
    
    if search_n in content:
        new_content = content.replace(search_n, replacement_text)
        print(f"[{patch_id}] Found pattern with \\n")
    elif search_rn in content:
        new_content = content.replace(search_rn, replacement_text)
        print(f"[{patch_id}] Found pattern with \\r\\n")
    else:
        # Fallback: try to find the starting line of the pattern and a block
        print(f"[{patch_id}] Error: Exact pattern not found. Check line endings or content.")
        return False
    
    with codecs.open(file_path, 'w', 'utf-8') as f:
        f.write(new_content)
    print(f"[{patch_id}] Successfully patched {file_path}")
    return True

client_path = r'c:\Sher_AI_Studio\projects\Shadow_Corp\Sprint_bot\bot\handlers\client.py'

# 1. Identify and replace the broken task_level_selection_handler and confirm_task_handler
# We'll replace the entire block from the start of task_level_selection_handler to the end of the file (as it's the last part)
# or at least a large enough chunk to be safe.

search_logic = """@client_router.callback_query(F.data.startswith("task_level:"))
async def task_level_selection_handler(callback: types.CallbackQuery, state: FSMContext, bot: Bot):"""

# Since we know the file ends with those handlers, we can just find where it starts and replace until the end.
with codecs.open(client_path, 'r', 'utf-8') as f:
    full_content = f.read()

start_index = full_content.find(search_logic)
if start_index != -1:
    prefix = full_content[:start_index]
    
    new_tail = """@client_router.callback_query(F.data.startswith("task_level:"))
async def task_level_selection_handler(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    user = await FirestoreDB.get_user(callback.from_user.id)
    if not user: return
    
    level_str = callback.data.split(":")[1]
    level_map = {"light": 1, "medium": 2, "hard": 3}
    level_val = level_map.get(level_str, 2)
    
    # Save the selected level for the day
    await FirestoreDB.update_user(user['id'], {"current_day_level": level_val})
    
    from utils.gsheets_api import get_task_2_0
    from utils.timezone_utils import get_user_current_day
    
    start_date = user.get('sprint_start_date') or user.get('created_at')
    day = get_user_current_day(start_date, user.get('timezone', 'UTC+7'))
    task_data = await get_task_2_0(day, user.get('scenario_type', 'Sovereign'))
    
    if not task_data:
        await callback.answer("Ошибка: данные задачи не найдены.")
        return
        
    task_text = task_data.get(f'task_{level_str}') or task_data.get('task_medium') or "Задача на сегодня загружается..."
    context_text = task_data.get('theory') or ""
    tool_text = task_data.get('guard_trap') or ""
    
    # Use triple quotes to avoid f-string termination issues and handle newlines cleanly
    full_task_msg = (
        f"🎯 {hbold('ТВОЕ ЗАДАНИЕ (' + level_str.upper() + ')')}\\n\\n"
        f"{task_text}\\n\\n"
        f"🔍 {hbold('КОНТЕКСТ')}\\n"
        f"{context_text}\\n\\n"
        f"🛠 {hbold('ИНСТРУМЕНТ')}\\n"
        f"{tool_text}\\n\\n"
        f"🏁 {hbold('Когда закончишь, пришли отчет текстом или голосом.')}"
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Принять и начать", callback_data=f"confirm_task:{level_str}")
    builder.button(text="⬅️ Изменить уровень", callback_data="change_task_level")
    builder.adjust(1)
    
    await callback.message.edit_text(
        full_task_msg, 
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@client_router.callback_query(F.data == "edit_log")
async def edit_log_handler(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_text("Хорошо, давай попробуем еще раз. 🎙\\nПришли исправленное сообщение или запиши новое аудио.")
    from bot.states import ClientStates
    await state.set_state(ClientStates.waiting_for_log)

@client_router.callback_query(F.data.startswith("confirm_task:"))
async def confirm_task_handler(callback: types.CallbackQuery, bot: Bot):
    level_str = callback.data.split(":")[1]
    level_names = {"light": "Light", "medium": "Medium", "hard": "Hard"}
    user = await FirestoreDB.get_user(callback.from_user.id)
    if not user: return
    
    from datetime import datetime, timezone
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
        f"Уровень: {hbold(level_names.get(level_str, level_str.capitalize()))}\\n\\n"
        f"Действуй! Жду твой отчет вечером.",
        reply_markup=None
    )
    
    is_admin_user = callback.from_user.id in ADMIN_IDS
    await callback.message.answer(
        "Используй меню ниже для навигации.", 
        reply_markup=get_main_keyboard(is_admin=is_admin_user, is_active=True)
    )
    await callback.answer("Задание принято!")
"""
    # Replace single \n with real newlines in the replacement string
    # We use \\n in the code block above so it prints \n in the final file
    # Wait, actually if I use f"..." in this script, it will interpret \n
    # So I should use raw strings or escaped backslashes.
    
    with codecs.open(client_path, 'w', 'utf-8') as f:
        f.write(prefix + new_tail)
    print("Successfully rebuilt tail of client.py")
else:
    print("Could not find start of logic block.")
