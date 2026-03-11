import os
import re
from pathlib import Path

def replace_imports():
    root = Path('c:/ideas/eden')
    for py_file in root.rglob('*.py'):
        if any(p in py_file.parts for p in ['.venv', '.git', 'docs', 'db', 'migrations']):
            continue
        if py_file.name == 'orm.py':
            continue
            
        try:
            content = py_file.read_text(encoding='utf-8')
            
            # replace `from eden.orm import X` -> `from eden.orm import X`
            # and `from eden.orm import X` -> `from eden.orm import X`
            new_content = re.sub(r'from eden\.db(?:\.\w+)? import', r'from eden.orm import', content)
            
            if new_content != content:
                py_file.write_text(new_content, encoding='utf-8')
                print(f"Updated {py_file}")
                
        except Exception as e:
            pass

if __name__ == '__main__':
    replace_imports()
