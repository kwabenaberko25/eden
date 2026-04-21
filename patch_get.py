import sys

with open('eden/auth/backends/session.py', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('return await User.get(session, user_id)', 'return await User.get(session=session, id=user_id)')

with open('eden/auth/backends/session.py', 'w', encoding='utf-8') as f:
    f.write(text)

with open('eden/admin/views.py', 'r', encoding='utf-8') as f:
    text2 = f.read()

text2 = text2.replace('user = await User.get(session_db, str(request.session["_auth_user_id"]))', 'user = await User.get(session=session_db, id=str(request.session["_auth_user_id"]))')

with open('eden/admin/views.py', 'w', encoding='utf-8') as f:
    f.write(text2)

print('Done!')
