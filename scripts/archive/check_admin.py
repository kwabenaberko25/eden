from eden.admin import admin
from eden.auth.models import User
from eden.admin.models import AuditLog
from eden.auth.api_key_model import APIKey

# Trigger registration
admin.register_defaults()

print(f"User registered: {admin.is_registered(User)}")
print(f"AuditLog registered: {admin.is_registered(AuditLog)}")
print(f"APIKey registered: {admin.is_registered(APIKey)}")
print(f"Total registered: {len(admin._registry)}")
for m in admin._registry:
    print(f" - {m.__name__} ({m.__tablename__})")
