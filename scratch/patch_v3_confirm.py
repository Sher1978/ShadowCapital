import os
import codecs

def patch_file(file_path, patch_id, search_pattern, replacement_text):
    if not os.path.exists(file_path):
        print(f"[{patch_id}] Error: {file_path} not found")
        return False
    with codecs.open(file_path, 'r', 'utf-8') as f:
        content = f.read()
    
    # Try multiple line ending combinations
    for search_pat in [search_pattern.replace('\n', '\r\n'), search_pattern.replace('\r\n', '\n')]:
        if search_pat in content:
            new_content = content.replace(search_pat, replacement_text)
            with codecs.open(file_path, 'w', 'utf-8') as f:
                f.write(new_content)
            print(f"[{patch_id}] Successfully patched {file_path}")
            return True
            
    # Try searching for a subset of the pattern if long
    if "\n" in search_pattern:
        first_line = search_pattern.split("\n")[0].strip()
        print(f"[{patch_id}] Failed to find exact pattern. First line check for '{first_line}'...")
        if first_line in content:
             print(f"[{patch_id}] Partial match found for first line. Whitespace issue likely.")
    
    print(f"[{patch_id}] Error: Pattern not found")
    return False

client_path = r'c:\Sher_AI_Studio\projects\Shadow_Corp\Sprint_bot\bot\handlers\client.py'

# 3. Patch client.py - Fix Nav and Confirmation (Simpler search)
search_broken = """    # Restore main menu buttons
    is_admin = callback.from_user.id in ADMIN_IDS
    await callback.message.edit_text(
        full_task_msg, 
        reply_markup=get_main_keyboard(is_admin=is_admin, is_active=True)
    )"""

replace_fixed = """    # Corrected Navigation: Use Inline Buttons for Task acceptance
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Принять и начать", callback_data=f"confirm_task:{level_str}")
    builder.button(text="⬅️ Изменить уровень", callback_data="change_task_level")
    builder.adjust(1)
    
    await callback.message.edit_text(
        full_task_msg, 
        reply_markup=builder.as_markup()
    )"""

# Also ensure we add the handlers at the end if not present
# But for now let's just do the replacement.

patch_file(client_path, "CLIENT-NAVFIX-RETRY", search_broken, replace_fixed)

# Append the confirm_task_handler to the end of the file if it's not there
with codecs.open(client_path, 'r', 'utf-8') as f:
    content = f.read()

if 'async def confirm_task_handler' not in content:
    confirm_handler_code = """

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
    with codecs.open(client_path, 'a', 'utf-8') as f:
        f.write(confirm_handler_code)
    print("Added confirm_task_handler to end of client.py")
