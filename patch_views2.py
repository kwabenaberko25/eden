import sys

with open('eden/admin/views.py', 'r', encoding='utf-8') as f:
    content = f.read()

s1 = '''    # 1. Check if user is already in request.state (from session middleware)
    user = getattr(request.state, "user", None) or getattr(request, "user", None)
    if user:
        return user'''
r1 = '''    # 1. Check if user is already in request.state (from session middleware)
    user = getattr(request.state, "user", None) or getattr(request, "user", None)
    if user:
        return user
        
    # 1b. Fallback for manual session check if AuthenticationMiddleware was not run
    if hasattr(request, "session") and "_auth_user_id" in request.session:
        try:
            from eden.auth.models import User
            from eden.db import _MISSING
            session_db = getattr(request.state, "db", _MISSING)
            user = await User.get(session_db, str(request.session["_auth_user_id"]))
            if user:
                request.state.user = user
                return user
        except Exception as e:
            logger.error(f"ADMIN: Failed to load user from session: {e}")'''

if s1 in content:
    content = content.replace(s1, r1)
else:
    print("WARNING: s1 not found")

with open('eden/admin/views.py', 'w', encoding='utf-8') as f:
    f.write(content)

with open('tests/test_admin_auth.py', 'r', encoding='utf-8') as f:
    t_content = f.read()

t_content = t_content.replace('assert "session" in response.cookies', 'assert "eden_session" in response.cookies')

with open('tests/test_admin_auth.py', 'w', encoding='utf-8') as f:
    f.write(t_content)

print("Done")
