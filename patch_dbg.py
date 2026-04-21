import sys

with open('tests/test_admin_auth.py', 'r', encoding='utf-8') as f:
    text = f.read()

s = '''    response = await client.get("/admin/api/me")'''
r = '''    response = await client.get("/admin/api/me")
    print("Cookies inside response:", response.cookies)
    print("Response text:", response.text)'''

if s in text:
    text = text.replace(s, r)
else:
    print("Not found")

with open('tests/test_admin_auth.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("Done")
