import os

replacements = {
    "Shadow Friction Index": "Shadow Braking Index",
    "Индекс Трения": "Индекс Теневого Торможения",
    "Трение": "Торможение",
    "трение": "торможение",
    "Сопротивление": "Торможение",
    "сопротивление": "торможение",
    "Shershadow": "Human OS"
}

target_dirs = ["docs", "utils", "web", "database", "functions", "bot"]
extensions = (".md", ".py", ".txt", ".json", ".jsx", ".html", ".css")

for target_dir in target_dirs:
    if not os.path.exists(target_dir):
        continue
    for root, dirs, files in os.walk(target_dir):
        for file in files:
            if file.endswith(extensions):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    new_content = content
                    for old, new in replacements.items():
                        new_content = new_content.replace(old, new)
                    
                    if new_content != content:
                        with open(filepath, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        print(f"Updated: {filepath}")
                except Exception as e:
                    pass # Ignore binary or encoding errors
