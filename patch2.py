import codecs

ADMIN_FILE = r'c:\Sher_AI_Studio\projects\Shadow_Corp\Sprint_bot\bot\handlers\admin.py'

with codecs.open(ADMIN_FILE, 'r', 'utf-8') as f:
    content = f.read()

target1 = '''    for u in users:
        name = u.get('full_name') or f"ID: {u.get('tg_id')}"
        sfi = f"SFI: {round(u.get('sfi_index', 1.0), 2)}"
        builder.button(text=f"🚀 {name} ({sfi})", callback_data=f"view_stats_{u.get('tg_id')}")'''

replacement1 = '''    for u in users:
        name = u.get('full_name') or f"ID: {u.get('tg_id')}"
        sfi = f"SFI: {round(u.get('sfi_index', 1.0), 2)}"
        day = "?"
        start_date = u.get('sprint_start_date') or u.get('created_at')
        if start_date:
            try:
                if isinstance(start_date, str):
                    start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                if start_date.tzinfo is None:
                    start_date = start_date.replace(tzinfo=timezone.utc)
                delta = datetime.now(timezone.utc) - start_date
                day = max(1, delta.days + 1)
            except: pass
        builder.button(text=f"🚀 {name} (День {day}) | {sfi}", callback_data=f"view_stats_{u.get('tg_id')}")'''

target2 = '''    for u in users:
        name = u.get('full_name') or f"ID: {u.get('tg_id')}"
        builder.button(text=f"📁 {name}", callback_data=f"view_archived_{u.get('tg_id')}")'''

replacement2 = '''    for u in users:
        name = u.get('full_name') or f"ID: {u.get('tg_id')}"
        day = "?"
        start_date = u.get('sprint_start_date') or u.get('created_at')
        if start_date:
            try:
                if isinstance(start_date, str):
                    start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                if start_date.tzinfo is None:
                    start_date = start_date.replace(tzinfo=timezone.utc)
                delta = datetime.now(timezone.utc) - start_date
                day = max(1, delta.days + 1)
            except: pass
        builder.button(text=f"📁 {name} (Архив: День {day})", callback_data=f"view_archived_{u.get('tg_id')}")'''

content = content.replace(target1, replacement1)
content = content.replace(target2, replacement2)

with codecs.open(ADMIN_FILE, 'w', 'utf-8') as f:
    f.write(content)

print("admin.py updated with sprint days")
