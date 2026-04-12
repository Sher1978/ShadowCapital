import os
import re

# Comprehensive mapping of corrupt UTF-8 decoded as CP1251/CP1252 to correct Cyrillic
MOJIBAKE_MAP = {
    'РџСЂРѕСЂР°Р±РѕС‚РєР° РўРµРЅРё': 'Проработка Тени',
    'Р”РµРЅСЊ': 'День',
    'РїСЂРѕРґРѕР»Р¶Р°РµРј РїРѕРіСЂСѓР¶РµРЅРёРµ РІ С‚РІРѕРµ С‚РµРЅРµРІРѕРµ РєР°С‡РµСЃС‚РІРѕ.': 'продолжаем погружение в твое теневое качество.',
    'Р”РѕР±СЂРѕРµ СѓС‚СЂРѕ': 'Доброе утро',
    'в˜ЂпёЏ РЎ РЅРѕРІС‹Рј РґРЅРµРј': '☀️ С новым днем',
    'вњЁ РџСЂРёРІРµС‚': '✨ Привет',
    '🔥 РџСЂРµРєСЂР°СЃРЅРѕРµ СѓС‚СЂРѕ': '🔥 Прекрасное утро',
    'рџЊ🌟 Р”РѕР±СЂРѕРµ СѓС‚СЂРѕ': '🌟 Доброе утро',
    '✅ Р“РѕС‚РѕРІ Рє РІС‹РїРѕР»РЅРµРЅРёСЋ': '✅ Готов к выполнению',
    'рџ“ќ РЎРґР°С‚СЊ РѕС‚С‡РµС‚ СЃРµР№С‡Р°СЃ': '📝 Сдать отчет сейчас',
    'Р’С‹Р±РµСЂРё СѓСЂРѕРІРµРЅСЊ СЃР»РѕР¶РЅРѕСЃС‚Рё РЅР° СЃРµРіРѕРґРЅСЏ:': 'Выбери уровень сложности на сегодня:',
    'в—ЅпёЏ Light': '◽️ Light',
    'рџ”¶ Medium': '🔶 Medium',
    'Р Р°СЃСЃС‹Р»РєР° Р·Р°РІРµСЂС€РµРЅР°. РћС‚РїСЂР°РІР»РµРЅРѕ:': 'Рассылка завершена. Отправлено:',
    'С‡РµР».': 'чел.',
    'рџ“‹ {hbold(\'РўРµРєСЃС‚ СЃРѕРѕР±С‰РµРЅРёСЏ:\')}': '📋 {hbold(\'Текст сообщения:\')}',
    'рџ‘‘ {hbold(\'WEEKLY GROUP SUMMARY\')}': '👑 {hbold(\'WEEKLY GROUP SUMMARY\')}',
    '🌑 {hbold(\'Advisor, РІСЂРµРјСЏ СЃРєР°РЅРёСЂРѕРІР°РЅРёСЏ.\')}': '🌑 {hbold(\'Advisor, время сканирования.\')}',
    'РЎРёСЃС‚РµРјР° РѕР±РЅРѕРІРёР»Р° РїРѕРєР°Р·Р°С‚РµР»Рё SFI. Р’ В«РєСЂР°СЃРЅРѕР№ Р·РѕРЅРµВ» СЃРµР№С‡Р°СЃ': 'Система обновила показатели SFI. В «красной зоне» сейчас',
    'РїСЂРѕРІРµСЂСЊ РґРµС‚Р°Р»Рё РІ СЂР°Р·РґРµР»Рµ': 'проверь детали в разделе',
    'рџ“ќ Р—Р°РїРѕР»РЅРёС‚СЊ РѕС‚С‡РµС‚': '📝 Заполнить отчет',
    'вљ™пёЏ Р˜Р·РјРµРЅРёС‚СЊ РІСЂРµРјСЏ РґРѕСЃС‚Р°РІРєРё': '⚙️ Изменить время доставки',
    'РџРѕСЂР° РїСЂРёСЃС‚СѓРїР°С‚СЊ Рє СЂР°Р±РѕС‚Рµ.': 'Пора приступать к работе.',
    'Р”РѕР±Р°РІРёС‚СЊ Task': 'Добавить Task',
    'РќРѕРІРѕРµ Р·Р°РґР°РЅРёРµ СѓСЃРїРµС€РЅРѕ РґРѕР±Р°РІР»РµРЅРѕ': 'Новое задание успешно добавлено',
    'Р’С‹Р±РµСЂРё РґРµРЅСЊ': 'Выбери день',
    'РћС€РёР±РєР°': 'Ошибка',
    'Р©Р°РґСЏС‰РёР№': 'Щадящий',
    'РћР±С‹С‡РЅС‹Р№': 'Обычный',
    'Р–РµСЃС‚РєРёР№': 'Жесткий'
}

def repair_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        for mojibake, correct in MOJIBAKE_MAP.items():
            content = content.replace(mojibake, correct)
        
        if content != original_content:
            with open(filepath, 'w', encoding='utf-8', newline='') as f:
                f.write(content)
            print(f"Fixed encoding in: {filepath}")
            return True
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
    return False

def main():
    target_dirs = ['bot', 'utils', 'database']
    files_fixed = 0
    for d in target_dirs:
        if not os.path.exists(d): continue
        for root, _, files in os.walk(d):
            for file in files:
                if file.endswith('.py'):
                    if repair_file(os.path.join(root, file)):
                        files_fixed += 1
    
    # Also fix main.py
    if os.path.exists('main.py'):
        if repair_file('main.py'):
            files_fixed += 1
            
    print(f"Total files repaired: {files_fixed}")

if __name__ == '__main__':
    main()
