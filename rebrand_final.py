import os
replacements = {
    'Shadow Friction Index': 'Shadow Braking Index',
    'Индекс Трения': 'Индекс Теневого Торможения',
    'Трение': 'Торможение',
    'трение': 'торможение',
    'Сопротивление': 'Торможение',
    'сопротивление': 'торможение',
    'Shershadow': 'Human OS',
    'Shadow Assistant': 'Human OS Architect',
    'Guardian': 'System Security',
    'Friction': 'Braking',
    'Resistance': 'Braking',
    'Коуч': 'Архитектор',
    'Хранитель': 'Система безопасности'
}
dirs = ['docs', 'utils', 'web', 'database', 'functions', 'bot']
exts = ('.md', '.py', '.txt', '.json', '.jsx', '.html', '.css')
for d in dirs:
    if os.path.exists(d):
        for r, _, fs in os.walk(d):
            for f in fs:
                if f.endswith(exts):
                    p = os.path.join(r, f)
                    try:
                        with open(p, 'r', encoding='utf-8') as file:
                            c = file.read()
                        nc = c
                        for old, new in replacements.items():
                            nc = nc.replace(old, new)
                        if nc != c:
                            with open(p, 'w', encoding='utf-8') as file:
                                file.write(nc)
                            print(f'Updated: {p}')
                    except Exception as e:
                        pass
