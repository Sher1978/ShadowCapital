import os

target = r'c:\Sher_AI_Studio\projects\Shadow_Corp\Sprint_bot\bot\handlers\settings.py'
with open(target, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
skip_until = -1

for i, line in enumerate(lines):
    if i < skip_until: continue
    
    if '@settings_router.callback_query(F.data.startswith("admin:trigger_"))' in line:
        # Replacement block
        new_lines.append(line)
        new_lines.append('async def admin_trigger_handler(callback: types.CallbackQuery, bot: Bot):\n')
        new_lines.append('    try:\n')
        new_lines.append('        # Immediate answer to acknowledge the click\n')
        new_lines.append('        await callback.answer("⏳ Запуск процесса...", show_alert=False)\n')
        new_lines.append('        \n')
        new_lines.append('        # Update message to show progress\n')
        new_lines.append('        original_text = callback.message.text\n')
        new_lines.append('        await callback.message.edit_text(f"{original_text}\\n\\n⌛ {hbold(\'Процесс запущен...\')}")\n')
        new_lines.append('\n')
        new_lines.append('        if callback.data == "admin:trigger_morning":\n')
        new_lines.append('            from utils.scheduler import send_morning_impulse\n')
        new_lines.append('            count = await send_morning_impulse(bot)\n')
        new_lines.append('            await callback.message.edit_text(f"{original_text}\\n\\n✅ {hbold(\'Рассылка завершена!\')}\\nОтправлено: {count} чел.")\n')
        new_lines.append('            \n')
        new_lines.append('        elif callback.data == "admin:trigger_weekly":\n')
        new_lines.append('            from utils.scheduler import send_group_weekly_report\n')
        new_lines.append('            await send_group_weekly_report(bot)\n')
        new_lines.append('            await callback.message.edit_text(f"{original_text}\\n\\n✅ {hbold(\'Еженедельный отчет отправлен!\')}")\n')
        new_lines.append('\n')
        new_lines.append('    except Exception as e:\n')
        new_lines.append('        import logging\n')
        new_lines.append('        logging.error(f"Error in admin trigger: {e}")\n')
        new_lines.append('        try:\n')
        new_lines.append('            await callback.message.edit_text(f"{callback.message.text}\\n\\n❌ {hbold(\'Ошибка:\')} {str(e)[:100]}")\n')
        new_lines.append('        except: pass\n')
        
        # Skip original handler
        j = i + 1
        while j < len(lines) and '@settings_router' not in lines[j] and 'def ' not in lines[j]:
            j += 1
        # Also need to find end of original function
        while j < len(lines) and not lines[j].startswith('@settings_router') and not lines[j].startswith('def '):
            # We skip until next decorator or function
            j += 1
        
        # Wait, the search for end of function is tricky. 
        # I'll just skip lines until I reach the end of the admin_trigger_handler which I know is about 20 lines.
        # Safer: search for the next decorator.
        
        skip_until = j
        continue
    
    new_lines.append(line)

with open(target, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print('settings.py patched: Admin trigger feedback improved.')
