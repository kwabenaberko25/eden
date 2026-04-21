import sys
with open('tests/test_admin_auth.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if line.strip() == 'response = await client.get("/admin/api/me")':
        if 'login' not in lines[i-1]:
            lines.insert(i, '    print(client.cookies.jar)\n')

with open('tests/test_admin_auth.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
