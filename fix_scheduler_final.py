import sys
import os

def fix_scheduler():
    path = r'c:\Sher_AI_Studio\projects\Shadow_Corp\Sprint_bot\utils\scheduler.py'
    if not os.path.exists(path):
        print(f"Error: {path} not found")
        return

    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Line 53 (index 52)
    lines[52] = '        text = f"🚩 {hbold(\'Контроль дедлайна:\')} Все отчеты сданы вовремя. Саботажа не обнаружено."\n'
    
    # Line 56 (index 55)
    lines[55] = '            f"🚩 {hbold(\'Внимание: Сбор логов завершен.\')}\\n\\n"\n'
    
    # Line 57 (index 56)
    lines[56] = '            f"Эти пользователи НЕ сдали отчет вовремя:\\n"\n'

    # Line 173 (index 172)
    lines[172] = '                f"☀️ С новым днем{name_suffix}!",\n'

    # Line 292 (index 291)
    lines[291] = '                    "❓ КАК СЕГОДНЯ ПРОЯВИЛОСЬ ТВОЕ ТЕНЕВОЕ КАЧЕСТВО?\\n\\n"\n'
    
    # Line 293 (index 292)
    lines[292] = '                    "❓ КАКОЕ СОПРОТИВЛЕНИЕ ТЫ ПОЧУВСТВОВАЛА(А)?\\n\\n"\n'

    # Line 305 (index 304)
    lines[304] = '            builder.button(text="⚙️ Изменить время доставки", callback_data="edit_delivery_times")\n'

    with open(path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print("Successfully patched utils/scheduler.py with direct line replacement.")

if __name__ == "__main__":
    fix_scheduler()
