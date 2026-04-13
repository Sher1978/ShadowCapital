import os

def restore():
    p = r'c:\Sher_AI_Studio\projects\Shadow_Corp\Sprint_bot\utils\scheduler.py'
    if not os.path.exists(p):
        print(f"Error: {p} not found")
        return
        
    with open(p, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    # Final cleanup of remaining mojibake in scheduler.py
    # Indices are based on current 455-line file version
    
    # 1. Morning greeting emoji (Line 173)
    lines[172] = '                f"☀️ С новым днем{name_suffix}!",\n'
    
    # 2. Evening questions fallback (Line 292-293)
    lines[291] = '                    "❓ КАК СЕГОДНЯ ПРОЯВИЛОСЬ ТВОЕ ТЕНЕВОЕ КАЧЕСТВО?\\n\\n"\n'
    lines[292] = '                    "❓ КАКОЕ СОПРОТИВЛЕНИЕ ТЫ ПОЧУВСТВОВАЛА(А)?\\n\\n"\n'
    
    # 3. Evening button (Line 305)
    lines[304] = '            builder.button(text="⚙️ Изменить время доставки", callback_data="edit_delivery_times")\n'
    
    with open(p, 'w', encoding='utf-8', newline='\n') as f:
        f.writelines(lines)
    print("Restore complete.")

if __name__ == "__main__":
    restore()
