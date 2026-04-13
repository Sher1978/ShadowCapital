import os

def patch_file(filepath, replacements):
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    for old, new in replacements.items():
        content = content.replace(old, new)
    
    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Successfully patched {filepath}")
    else:
        print(f"No changes needed for {filepath}")

# Mapping for utils/scheduler.py - Second Pass
scheduler_replacements_v2 = {
    "Р’СЃРµ РѕС‚С‡РµС‚С‹ СЃРґР°РЅС‹ РІРѕРІСЂРµМЏРјСЏ": "Все отчеты сданы вовремя",
    "РЎР°Ð±ÐѕÑ‚Ð°Ð¶Р° РЅРµ РѕÐ±РЅР°Ñ€ÑƒÐ¶ÐµÐЅÐѕ": "Саботажа не обнаружено",
    "Р’РЅРёРјР°РЅРёРµ: РЎР±Р¾СЂ Р»Р¾РіР¾РІ Р·Р°РІРµСЂС€РµРЅ.": "Внимание: Сбор логов завершен.",
    "Р­С‚Рё РїРѕР»СЊР·РѕРІР°С‚РµР»Рё РќР• СЃРґР°Р»Рё РѕС‚С‡РµС‚ РІРѕРІСЂРµМЏРјСЏ:": "Эти пользователи НЕ сдали отчет вовремя:",
    "РЎРІРѕРґРєР° РёРЅСЃР°Р№С‚РѕРІ РіРѕС‚РѕРІР°.": "Сводка инсайтов готова.",
    "РџСЂРѕРґРѕР»Р¶Р°РµРј РїРѕРіСЂСѓР¶РµРЅРёРµ РІ С‚РІРѕРµ С‚РµРЅРµРІРѕРµ РєР°С‡РµСЃС‚РІРѕ.": "Продолжаем погружение в твое теневое качество.",
    "Р’СЃРїРѕРјРЅРё СЃРµРіРѕРґРЅСЏС€РЅРёР№ РґРµРЅСЊ:": "Вспомни сегодняшний день:",
    "РљРђРљ СЃРµРіРѕРґРЅСЏ РїСЂРѕСЏРІРёР»РѕСЃСЊ": "КАК СЕГОДНЯ ПРОЯВИЛОСЬ",
    "РљРђРљРћР• РЎРћРџР РћРўР˜Р’Р›Р•РќР˜Р•": "КАКОЕ СОПРОТИВЛЕНИЕ",
    "Р˜Р·РјРµРЅРёС‚СЊ РІСЂРµРјСЏ РґРѕСЃС‚Р°РІРєРё": "Изменить время доставки",
    "в˜ЂпёЏ": "☀️",
    "РЎ РЅРѕРІС‹Рј РґРЅРµРј": "С новым днем"
}

if __name__ == "__main__":
    patch_file('utils/scheduler.py', scheduler_replacements_v2)
