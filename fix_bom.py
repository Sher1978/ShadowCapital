import os

def strip_bom(filepath):
    if not os.path.exists(filepath):
        print(f'{filepath} does not exist.')
        return
    
    with open(filepath, 'rb') as f:
        content = f.read()
    
    # Check for UTF-8 BOM
    if content.startswith(b'\xef\xbb\xbf'):
        print(f'BOM found in {filepath}. Removing...')
        with open(filepath, 'wb') as f:
            f.write(content[3:])
        print(f'BOM removed from {filepath}.')
    else:
        print(f'No BOM found in {filepath}.')

strip_bom(r'c:\Sher_AI_Studio\projects\Shadow_Corp\Sprint_bot\utils\scheduler.py')
strip_bom(r'c:\Sher_AI_Studio\projects\Shadow_Corp\Sprint_bot\bot\handlers\settings.py')
strip_bom(r'c:\Sher_AI_Studio\projects\Shadow_Corp\Sprint_bot\main.py')
strip_bom(r'c:\Sher_AI_Studio\projects\Shadow_Corp\Sprint_bot\utils\gsheets_api.py')
