import codecs

CLIENT_FILE = r'c:\Sher_AI_Studio\projects\Shadow_Corp\Sprint_bot\bot\handlers\client.py'

with codecs.open(CLIENT_FILE, 'r', 'utf-8') as f:
    content = f.read()

target = '''    await sync_user_to_sheets({
        "user_id": user.get('tg_id'),
        "name": user.get('full_name'),
        "target_quality": user.get('target_quality_l1'),
        "scenario": user.get('scenario_type'),
        "red_flags": update_data.get("red_flags_count", user.get('red_flags_count', 0)),
        "sfi_index": math_sfi / 100.0,
        "last_insight": update_data["last_insight"]
    })'''

replacement = '''    await sync_user_to_sheets({
        "user_id": user.get('tg_id'),
        "name": user.get('full_name'),
        "target_quality": user.get('target_quality_l1'),
        "scenario": user.get('scenario_type'),
        "focus_currency": user.get('focus_currency', 'N/A'),
        "red_flags": update_data.get("red_flags_count", user.get('red_flags_count', 0)),
        "sfi_index": math_sfi / 100.0,
        "last_insight": update_data["last_insight"]
    })'''

content = content.replace(target, replacement)
with codecs.open(CLIENT_FILE, 'w', 'utf-8') as f:
    f.write(content)

print("client.py updated")

ADMIN_FILE = r'c:\Sher_AI_Studio\projects\Shadow_Corp\Sprint_bot\bot\handlers\admin.py'

with codecs.open(ADMIN_FILE, 'r', 'utf-8') as f:
    content = f.read()

target1 = '''    await sync_user_to_sheets({
        "user_id": data['tg_id'],
        "name": data['full_name'],
        "target_quality": data['quality_name'],
        "scenario": scenario_type,
        "red_flags": 0
    })'''

replacement1 = '''    await sync_user_to_sheets({
        "user_id": data['tg_id'],
        "name": data['full_name'],
        "target_quality": data['quality_name'],
        "scenario": scenario_type,
        "focus_currency": "N/A",
        "red_flags": 0
    })'''

target2 = '''        await sync_user_to_sheets({
            "user_id": user.get('tg_id'),
            "name": user.get('full_name'),
            "target_quality": new_quality,
            "scenario": user.get('scenario_type'),
            "red_flags": user.get('red_flags_count') or 0,
            "sfi_index": user.get('sfi_index') or 1.0
        })'''

replacement2 = '''        await sync_user_to_sheets({
            "user_id": user.get('tg_id'),
            "name": user.get('full_name'),
            "target_quality": new_quality,
            "scenario": user.get('scenario_type'),
            "focus_currency": user.get('focus_currency', 'N/A'),
            "red_flags": user.get('red_flags_count') or 0,
            "sfi_index": user.get('sfi_index') or 1.0
        })'''

target3 = '''        await sync_user_to_sheets({
            "user_id": user.get('tg_id'),
            "name": user.get('full_name'),
            "target_quality": user.get('target_quality_l1'),
            "scenario": new_scenario,
            "red_flags": user.get('red_flags_count') or 0,
            "sfi_index": user.get('sfi_index') or 1.0
        })'''

replacement3 = '''        await sync_user_to_sheets({
            "user_id": user.get('tg_id'),
            "name": user.get('full_name'),
            "target_quality": user.get('target_quality_l1'),
            "scenario": new_scenario,
            "focus_currency": user.get('focus_currency', 'N/A'),
            "red_flags": user.get('red_flags_count') or 0,
            "sfi_index": user.get('sfi_index') or 1.0
        })'''

content = content.replace(target1, replacement1)
content = content.replace(target2, replacement2)
content = content.replace(target3, replacement3)

with codecs.open(ADMIN_FILE, 'w', 'utf-8') as f:
    f.write(content)

print("admin.py updated")
