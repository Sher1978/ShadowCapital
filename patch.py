import os

file_path = r"c:\Sher_AI_Studio\projects\Shadow_Corp\Sprint_bot\utils\gsheets_api.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Replace the specific target content
target = 'SHEET_NAME_TASK_ENGINE = "NEW_TASK_ENGINE"'
replacement = 'SHEET_NAME_TASK_ENGINE = "TASK_ENGINE_2"'

new_content = content.replace(target, replacement)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(new_content)

print("Patch applied successfully.")
