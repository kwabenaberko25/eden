import re

with open('tests/test_admin_auth.py', 'r') as f:
    text = f.read()

text = text.replace('"StrongPassw0rd!": "StrongPassw0rd!"', '"password": "StrongPassw0rd!"')
text = text.replace('"StrongPassw0rd!": "wrong"', '"password": "wrong"')

with open('tests/test_admin_auth.py', 'w') as f:
    f.write(text)
    
with open('eden/admin/dashboard_routes.py', 'r') as f:
    text = f.read()
    
text = text.replace('router.include_router(panel.router, prefix="/flags")', 'router.include_router(panel.router, prefix=f"{prefix}/flags")')

with open('eden/admin/dashboard_routes.py', 'w') as f:
    f.write(text)
