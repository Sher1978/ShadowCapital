import os
import re

target = r'c:\Sher_AI_Studio\projects\Shadow_Corp\Sprint_bot\bot\handlers\client.py'
with open(target, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Remove the first (simpler) handler
handler1_pattern = r'@client_router\.callback_query\(F\.data\.startswith\("task_level:"\)\)\nasync def task_level_selection_handler\(callback: types\.CallbackQuery, bot: Bot\):.*?await callback\.answer\(\)'
content = re.sub(handler1_pattern, '', content, flags=re.DOTALL)

# 2. Fix the second (complex) handler to be perfect
# I will keep the one at the end but make sure it has 'bot: Bot' and 'state: FSMContext'
# Actually, I'll just replace the whole block from 888 to 927 with a clean one.

handler2_pattern = r'@client_router\.callback_query\(F\.data\.startswith\("task_level:"\)\)\nasync def task_level_selection_handler\(callback: types\.CallbackQuery, state: FSMContext, bot: Bot\):.*?await callback\.answer\(\)'
# Note: I'll use a more surgical approach if possible, but the file is large.

# Since the file is large, I'll use line-based patching for safety.
lines = content.splitlines(True)
new_lines = []
skip_until = -1

for i, line in enumerate(lines):
    if i < skip_until: continue
    
    # Identify first handler (around line 742)
    if '@client_router.callback_query(F.data.startswith("task_level:"))' in line and i < 800:
        # Looking for the first one
        # We skip it
        j = i
        while j < len(lines) and 'await callback.answer()' not in lines[j]:
            j += 1
        skip_until = j + 1
        continue
    
    new_lines.append(line)

with open(target, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print('client.py patched: Duplicate handler removed.')
