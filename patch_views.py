import sys

with open('eden/admin/views.py', 'r', encoding='utf-8') as f:
    content = f.read()

s1 = '''    # 1. Try from request.app (Eden/Starlette application)
    secret = getattr(request.app, "secret_key", None)'''
r1 = '''    # 1. Try from request.app (Eden/Starlette application)
    secret = getattr(request.app, "secret_key", None)
    if not secret and hasattr(request.app, "config"):
        secret = getattr(request.app.config, "secret_key", None)'''

s2 = '''                        if not is_safe_url(next_url, request):
                            next_url = "/admin/"

                        from eden.responses import RedirectResponse
                        response = RedirectResponse(url=next_url, status_code=303)'''
r2 = '''                        if not is_safe_url(next_url, request):
                            next_url = "/admin/"

                        if "?" in next_url:
                            next_url += f"&token={token}"
                        else:
                            next_url += f"?token={token}"

                        from eden.responses import RedirectResponse
                        response = RedirectResponse(url=next_url, status_code=303)'''

if s1 in content:
    content = content.replace(s1, r1)
else:
    print("WARNING: s1 not found")

if s2 in content:
    content = content.replace(s2, r2)
else:
    print("WARNING: s2 not found")

with open('eden/admin/views.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Done")
