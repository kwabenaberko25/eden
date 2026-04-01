import os
import re
import sys

def fix_lints(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    new_lines = []
    for i, line in enumerate(lines):
        # MD012: Multiple consecutive blank lines
        if i > 0 and line.strip() == "" and new_lines[-1].strip() == "":
            continue
        
        # MD022: Headings should be surrounded by blank lines
        if line.startswith('#'):
            if i > 0 and new_lines[-1].strip() != "":
                new_lines.append("\n")
            new_lines.append(line)
            if i < len(lines) - 1 and lines[i+1].strip() != "":
                new_lines.append("\n")
            continue

        # MD032: Lists should be surrounded by blank lines
        if re.match(r'^\s*[\*\-\+] ', line) or re.match(r'^\s*\d+\. ', line):
            if i > 0 and not (re.match(r'^\s*[\*\-\+] ', new_lines[-1]) or re.match(r'^\s*\d+\. ', new_lines[-1]) or new_lines[-1].strip() == ""):
                new_lines.append("\n")
            new_lines.append(line)
            if i < len(lines) - 1 and not (re.match(r'^\s*[\*\-\+] ', lines[i+1]) or re.match(r'^\s*\d+\. ', lines[i+1]) or lines[i+1].strip() == ""):
                new_lines.append("\n")
            continue

        new_lines.append(line)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

if __name__ == "__main__":
    for arg in sys.argv[1:]:
        if os.path.exists(arg):
            print(f"Fixing lints in {arg}...")
            fix_lints(arg)
