import codecs

def fix_indent(file_path):
    with codecs.open(file_path, 'r', 'utf-8') as f:
        lines = f.readlines()
    
    new_lines = []
    for i, line in enumerate(lines):
        # Specific check for the mismatched indent lines
        if 'day = get_user_current_day' in line and (line.lstrip() != line):
            # Calculate correct indent: look at previous non-empty line
            # Default to 12 spaces (3 levels of 4)
            corrected = line.strip()
            # Find the line that should be the parent
            new_lines.append('            ' + corrected + '\n')
        else:
            new_lines.append(line)
            
    with codecs.open(file_path, 'w', 'utf-8') as f:
        f.writelines(new_lines)

fix_indent(r'c:\Sher_AI_Studio\projects\Shadow_Corp\Sprint_bot\utils\scheduler.py')
print('Indentation fixed')
