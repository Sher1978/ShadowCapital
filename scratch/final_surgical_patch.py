import os

target_file = r"c:\Sher_AI_Studio\projects\Shadow_Corp\Sprint_bot\utils\scheduler.py"

with open(target_file, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Line 173 (0-indexed 172): greeting emoji
lines[172] = '                f"☀️ С новым днем{name_suffix}!",\n'

# Line 292 (0-indexed 291): evening question 1
lines[291] = '                    "❓ КАК СЕГОДНЯ ПРОЯВИЛОСЬ ТВОЕ ТЕНЕВОЕ КАЧЕСТВО?\\n\\n"\n'

# Line 293 (0-indexed 292): evening question 2
lines[292] = '                    "❓ КАКОЕ СОПРОТИВЛЕНИЕ ТЫ ПОЧУВСТВОВАЛА(А)?\\n\\n"\n'

# Line 305 (0-indexed 304): setting button
lines[304] = '            builder.button(text="⚙️ Изменить время доставки", callback_data="edit_delivery_times")\n'

with open(target_file, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("Surgical patch applied successfully.")
