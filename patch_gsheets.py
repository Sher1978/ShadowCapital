import sys

target = r'c:\Sher_AI_Studio\projects\Shadow_Corp\Sprint_bot\utils\gsheets_api.py'
with open(target, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace old occurrences
content = content.replace('"CONTENT_TIMELINE"', 'SHEET_NAME_TASK_ENGINE')
content = content.replace("'CONTENT_TIMELINE'", "f'{SHEET_NAME_TASK_ENGINE}'")
content = content.replace('CONTENT_TIMELINE sheet', 'task engine sheet')

with open(target, 'w', encoding='utf-8') as f:
    f.write(content)

print('Patch applied successfully.')
