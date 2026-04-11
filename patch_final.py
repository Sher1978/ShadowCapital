import codecs

SCHEDULER_FILE = r'c:\Sher_AI_Studio\projects\Shadow_Corp\Sprint_bot\utils\scheduler.py'
CLIENT_FILE = r'c:\Sher_AI_Studio\projects\Shadow_Corp\Sprint_bot\bot\handlers\client.py'
AUDIT_FILE = r'c:\Sher_AI_Studio\projects\Shadow_Corp\Sprint_bot\bot\handlers\audit.py'

# 1. Fix scheduler.py
with codecs.open(SCHEDULER_FILE, 'r', 'utf-8') as f:
    content = f.read()
target_sch = "async def request_evening_logs(bot: Bot, user: dict = None) -> int:"
replacement_sch = "async def request_evening_logs(bot: Bot, user: dict = None, bypass_audit: bool = False) -> int:"
content = content.replace(target_sch, replacement_sch)
with codecs.open(SCHEDULER_FILE, 'w', 'utf-8') as f:
    f.write(content)

# 2. Fix client.py
with codecs.open(CLIENT_FILE, 'r', 'utf-8') as f:
    content = f.read()

# First call context
target_cl1 = '''    analysis = await analyze_sabotage(
        content, 
        quality_name=user.get('target_quality_l1', "Unknown"),
        scenario_type=user.get('scenario_type', "N/A")
    )'''
replacement_cl1 = '''    analysis = await analyze_sabotage(
        content, 
        quality_name=user.get('target_quality_l1', "Unknown"),
        scenario_type=user.get('scenario_type', "N/A"),
        focus_currency=user.get('focus_currency', "N/A")
    )'''

# Second call context
target_cl2 = '''        analysis = await analyze_sabotage(
            content, 
            quality_name=user.get('target_quality_l1', "Unknown"),
            scenario_type=user.get('scenario_type', "N/A"),
            guard_trap=guard_trap
        )'''
replacement_cl2 = '''        analysis = await analyze_sabotage(
            content, 
            quality_name=user.get('target_quality_l1', "Unknown"),
            scenario_type=user.get('scenario_type', "N/A"),
            guard_trap=guard_trap,
            focus_currency=user.get('focus_currency', "N/A")
        )'''

content = content.replace(target_cl1, replacement_cl1)
content = content.replace(target_cl2, replacement_cl2)
with codecs.open(CLIENT_FILE, 'w', 'utf-8') as f:
    f.write(content)

# 3. Fix audit.py
with codecs.open(AUDIT_FILE, 'r', 'utf-8') as f:
    content = f.read()

target_audit = '''    # Update main user document for AI context
    await FirestoreDB.update_user(user['id'], {"focus_currency": focus})'''
replacement_audit = '''    # Update main user document for AI context
    await FirestoreDB.update_user(user['id'], {"focus_currency": focus})
    
    # Sync to GSheets
    from utils.gsheets_api import sync_user_to_sheets
    try:
        await sync_user_to_sheets(user['id'], {"focus_currency": focus})
    except Exception as e:
        logging.error(f"Failed to sync focus to sheets: {e}")'''

content = content.replace(target_audit, replacement_audit)
with codecs.open(AUDIT_FILE, 'w', 'utf-8') as f:
    f.write(content)

print("Patch applied successfully")
