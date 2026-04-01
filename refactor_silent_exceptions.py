import os
import re

def refactor_silent_exceptions(root_dir):
    pattern = re.compile(r'([\t ]*)except Exception as [a-zA-Z_0-9]+:\s*\n\s+pass')
    
    files_changed = 0
    for dirpath, _, filenames in os.walk(root_dir):
        if '__pycache__' in dirpath:
            continue
        for filename in filenames:
            if not filename.endswith('.py'):
                continue
            
            filepath = os.path.join(dirpath, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if pattern.search(content):
                def replace_func(match):
                    indent = match.group(1)
                    return (
                        f"{indent}except Exception as e:\n"
                        f"{indent}    from eden.logging import get_logger\n"
                        f"{indent}    get_logger(__name__).error(\"Silent exception caught: %s\", e, exc_info=True)"
                    )
                
                new_content = pattern.sub(replace_func, content)
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"Refactored: {filepath}")
                files_changed += 1

    print(f"Total files refactored: {files_changed}")

if __name__ == '__main__':
    refactor_silent_exceptions('eden')
