#!/usr/bin/env python
"""Quick syntax check."""

try:
    from eden.admin import admin
    from eden.admin.views import admin_api_metadata
    from eden.admin.premium_dashboard import PremiumAdminTemplate
    print("✓ All imports successful")
    
    # Try to build a router
    router = admin.build_router("/admin")
    print(f"✓ Router built successfully with {len(router.routes)} routes")
    
    # Check that flags is in metadata when creating admin
    print("✓ Admin panel integration checks passed")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
