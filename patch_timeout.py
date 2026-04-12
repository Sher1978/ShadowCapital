import sys

target = r'c:\Sher_AI_Studio\projects\Shadow_Corp\Sprint_bot\bot\handlers\settings.py'
with open(target, 'r', encoding='utf-8') as f:
    content = f.read()

search_str = '''    action = callback.data.replace("trigger_", "")
    logger.info(f"⚡ [ADMIN] Manually triggering action: {action}")'''

replace_str = '''    action = callback.data.replace("trigger_", "")
    logger.info(f"⚡ [ADMIN] Manually triggering action: {action}")
    
    # ПРЕДВЕЩАТЕЛЬНЫЙ ОТВЕТ НА КОЛБЕК, ЧТОБЫ НЕ БЫЛО ТАЙМАУТА (Query is too old)
    try:
        await callback.answer("Запускаю процесс, это может занять время...")
    except Exception:
        pass'''

if search_str in content:
    content = content.replace(search_str, replace_str)
    
    # Remove the late callback answer
    content = content.replace('        await callback.answer("Запущено!")\n', '')
    
    with open(target, 'w', encoding='utf-8') as f:
        f.write(content)
    print('Patch applied successfully to settings.py.')
else:
    print('Search string not found!')
