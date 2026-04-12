import os
import codecs

def patch_file(file_path, search_pattern, replacement_text):
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found")
        return False
    
    with codecs.open(file_path, 'r', 'utf-8') as f:
        content = f.read()
    
    # Normalize line endings for the search
    search_pattern_rn = search_pattern.replace('\n', '\r\n')
    search_pattern_n = search_pattern.replace('\r\n', '\n')
    
    if search_pattern_n in content:
        new_content = content.replace(search_pattern_n, replacement_text)
    elif search_pattern_rn in content:
        new_content = content.replace(search_pattern_rn, replacement_text)
    else:
        print(f"Error: Pattern not found in {file_path}")
        # Print a snippet of content for debugging
        print("Search pattern was:")
        print(repr(search_pattern_n))
        return False
    
    with codecs.open(file_path, 'w', 'utf-8') as f:
        f.write(new_content)
    print(f"Successfully patched {file_path}")
    return True

# --- Patch builders.py ---
builders_path = r'c:\Sher_AI_Studio\projects\Shadow_Corp\Sprint_bot\bot\keyboards\builders.py'
search_builders = '    builder.button(text="🎯 Моя цель")\n    builder.button(text="📝 Вечерний Отчет")'
replace_builders = '    builder.button(text="🎯 Моя цель")\n    builder.button(text="🎯 Задание")\n    builder.button(text="📝 Вечерний Отчет")'

patch_file(builders_path, search_builders, replace_builders)


# --- Patch client.py ---
client_path = r'c:\Sher_AI_Studio\projects\Shadow_Corp\Sprint_bot\bot\handlers\client.py'

# 1. Add manual_task_trigger
search_manual = '@client_router.message(F.text == "🎯 Моя цель")\nasync def my_goal_handler(message: types.Message) -> None:'
replace_manual = """@client_router.message(F.text == "🎯 Задание")
async def manual_task_trigger(message: types.Message, state: FSMContext, bot: Bot):
    user = await FirestoreDB.get_user(message.from_user.id)
    if not user: return
    
    # Check if user is active
    is_admin_user = message.from_user.id in ADMIN_IDS
    if user.get('status') != "active" and not is_admin_user:
        await message.answer("Для получения заданий твой профиль должен быть активирован.")
        return

    # Trigger task selection flow
    from utils.gsheets_api import get_task_2_0
    from utils.timezone_utils import get_user_current_day
    
    start_date = user.get('sprint_start_date') or user.get('created_at')
    day = get_user_current_day(start_date, user.get('timezone', 'UTC+7'))
    task_data = await get_task_2_0(day, user.get('scenario_type', 'Sovereign'))
    
    if not task_data:
        await message.answer("Ошибка: данные задания не найдены.")
        return
        
    theory = task_data.get('theory', 'Пора приступать к работе.')
    day_name = task_data.get('day_name', f"День {day}")
    quality = user.get('target_quality_l1') or user.get('target_quality') or 'Проработка Тени'
    phase_text = f"{hitalic(task_data.get('phase'))}\\n\\n" if task_data.get('phase') else ""
    
    text = (
        f"💎 {hbold(quality)}: {day_name}\\n\\n"
        f"{phase_text}"
        f"{theory}\\n\\n"
        f"Выбери уровень сложности на сегодня:"
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text="◽️ Light", callback_data="task_level:light")
    builder.button(text="🔶 Medium", callback_data="task_level:medium")
    builder.button(text="🔥 Hard", callback_data="task_level:hard")
    builder.adjust(3)
    
    await message.answer(text, reply_markup=builder.as_markup())

@client_router.message(F.text == "🎯 Моя цель")
async def my_goal_handler(message: types.Message) -> None:"""

patch_file(client_path, search_manual, replace_manual)

# 2. Fix task_level_selection_handler broken markup and add confirmation handler
search_broken = """    # Restore main menu buttons
    is_admin = callback.from_user.id in ADMIN_IDS
    await callback.message.edit_text(
        full_task_msg, 
        reply_markup=get_main_keyboard(is_admin=is_admin, is_active=True)
    )
    await callback.answer()"""

replace_fixed = """    # Corrected Navigation: Use Inline Buttons for Task acceptance
    builder = InlineKeyboardBuilder()
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
    
    user = await FirestoreDB.get_user(callback.from_user.id)
    if not user: return
    
    # Notify Admin
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
    
    # Refresh the physical main menu
    is_admin_user = callback.from_user.id in ADMIN_IDS
    await callback.message.answer(
        "Используй меню ниже для навигации.", 
        reply_markup=get_main_keyboard(is_admin=is_admin_user, is_active=True)
    )
    await callback.answer("Задание принято!")"""

patch_file(client_path, search_broken, replace_fixed)
