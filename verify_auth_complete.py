#!/usr/bin/env python
"""Final verification of Eden authentication system exports."""

import sys

print("=" * 60)
print("EDEN AUTHENTICATION SYSTEM - FINAL VERIFICATION")
print("=" * 60)

# Test all exports
from eden import auth

# Count exports
exports = [item for item in dir(auth) if not item.startswith('_')]
print(f"\n✅ Total exports from eden.auth: {len(exports)}")

# Categories
models = ["User", "BaseUser", "SocialAccount", "APIKey"]
password = ["hash_password", "check_password", "hasher", "Argon2Hasher"]
rbac = ["default_rbac", "EdenRBAC", "apply_rbac_filter", "user_has_permission", 
        "user_has_role", "user_has_any_permission", "user_has_any_role"]
oauth = ["OAuthManager", "OAuthProvider"]
backends = ["AuthBackend", "JWTBackend", "SessionBackend", "APIKeyBackend"]
decorators = ["login_required", "roles_required", "permissions_required", 
              "require_permission", "is_authorized", "bind_user_principal"]
middleware = ["AuthenticationMiddleware"]
deps = ["get_current_user", "current_user"]
providers = ["JWTProvider"]
password_reset = ["PasswordResetToken", "PasswordResetService", "PasswordResetEmail", "password_reset_router"]

categories = {
    "Models": models,
    "Password": password,
    "RBAC": rbac,
    "OAuth": oauth,
    "Backends": backends,
    "Decorators": decorators,
    "Middleware": middleware,
    "Dependencies": deps,
    "Providers": providers,
    "Password Reset": password_reset,
}

print("\nExport Verification:")
all_verified = True
for category, items in categories.items():
    verified = [item for item in items if hasattr(auth, item)]
    status = "✅" if len(verified) == len(items) else "❌"
    print(f"{status} {category:20s}: {len(verified)}/{len(items)} items")
    if len(verified) != len(items):
        missing = [item for item in items if not hasattr(auth, item)]
        print(f"   Missing: {missing}")
        all_verified = False

print("\n" + "=" * 60)
if all_verified:
    print("✅ ALL AUTHENTICATION LAYERS VERIFIED AND EXPORTED")
    print("=" * 60)
    sys.exit(0)
else:
    print("❌ SOME EXPORTS MISSING")
    print("=" * 60)
    sys.exit(1)
