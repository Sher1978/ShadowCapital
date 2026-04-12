import sys

target = r'c:\Sher_AI_Studio\projects\Shadow_Corp\Sprint_bot\main.py'
with open(target, 'r', encoding='utf-8') as f:
    content = f.read()

search_str = 'logging.basicConfig('
replace_str = '''if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

logging.basicConfig('''

if search_str in content and 'io.TextIOWrapper' not in content:
    content = content.replace(search_str, replace_str)
    with open(target, 'w', encoding='utf-8') as f:
        f.write(content)
    print('Patch applied successfully.')
else:
    print('Already patched or not found.')
