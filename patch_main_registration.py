import os

target = r'c:\Sher_AI_Studio\projects\Shadow_Corp\Sprint_bot\main.py'
with open(target, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
imported = False
registered = False

for line in lines:
    # Add import
    if 'from bot.handlers.initiation import initiation_router' in line and not imported:
        new_lines.append(line)
        new_lines.append('        from bot.handlers.audit import audit_router\n')
        imported = True
        continue
    
    # Add registration
    if 'dp.include_router(initiation_router)' in line and not registered:
        new_lines.append(line)
        new_lines.append('        dp.include_router(audit_router)\n')
        registered = True
        continue
        
    new_lines.append(line)

with open(target, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
print('main.py patched successfully (audit_router registered).')
