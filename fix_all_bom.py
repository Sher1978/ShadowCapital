import os

def remove_all_bom(filepath):
    if not os.path.exists(filepath): return
    with open(filepath, 'rb') as f:
        content = f.read()
    
    new_content = content.replace(b'\xef\xbb\xbf', b'')
    if new_content != content:
        print(f'Removed BOM(s) from {filepath}')
        with open(filepath, 'wb') as f:
            f.write(new_content)
    else:
        print(f'No BOMs found in {filepath}')

files = [
    r'c:\Sher_AI_Studio\projects\Shadow_Corp\Sprint_bot\utils\scheduler.py',
    r'c:\Sher_AI_Studio\projects\Shadow_Corp\Sprint_bot\bot\handlers\settings.py',
    r'c:\Sher_AI_Studio\projects\Shadow_Corp\Sprint_bot\main.py',
    r'c:\Sher_AI_Studio\projects\Shadow_Corp\Sprint_bot\utils\gsheets_api.py'
]

for f in files:
    remove_all_bom(f)
