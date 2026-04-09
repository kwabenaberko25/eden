import os
import re

mappings = {
    r'tenancy\.md': 'tenancy-postgres.md',
    r'multi-tenancy\.md': 'multi-tenancy-masterclass.md',
    r'migrations\.md': 'orm-migrations.md',
    r'validation\.md': 'forms.md',
    r'csrf-protection\.md': 'security.md',
    r'auth-rbac\.md': 'security.md'
}

guides_dir = 'docs/guides'

for filename in os.listdir(guides_dir):
    if filename.endswith('.md'):
        path = os.path.join(guides_dir, filename)
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        new_content = content
        for pattern, replacement in mappings.items():
            new_content = re.sub(pattern, replacement, new_content)
        
        if new_content != content:
            print(f"Updating links in {filename}")
            with open(path, 'w', encoding='utf-8') as f:
                f.write(new_content)
