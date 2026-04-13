import os

def fix():
    # Use absolute path for safety
    target = r'c:\Sher_AI_Studio\projects\Shadow_Corp\Sprint_bot\utils\scheduler.py'
    
    with open(target, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    # Directly replace lines by index (1-indexed 173, 292, 293, 305)
    # Indices: 172, 291, 292, 304
    
    # 173: Morning greeting emoji
    lines[172] = '                f"☀️ С новым днем{name_suffix}!",\n'
    
    # 292: Evening question 1
    lines[291] = '                    "❓ КАК СЕГОДНЯ ПРОЯВИЛОСЬ ТВОЕ ТЕНЕВОЕ КАЧЕСТВО?\\n\\n"\n'
    
    # 293: Evening question 2
    lines[292] = '                    "❓ КАКОЕ СОПРОТИВЛЕНИЕ ТЫ ПОЧУВСТВОВАЛА(А)?\\n\\n"\n'
    
    # 305: Button text
    lines[304] = '            builder.button(text="⚙️ Изменить время доставки", callback_data="edit_delivery_times")\n'
    
    with open(target, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print("Execution complete: Remaining scheduler strings fixed.")

if __name__ == "__main__":
    fix()
