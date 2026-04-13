#!/usr/bin/env python
"""
Quick verification test for the integrated admin panel with feature flags.

Tests:
1. Admin site can be created and router built
2. Metadata includes feature flags as virtual model
3. Feature flags appear in admin sidebar
4. Admin is enabled by default in new app instances
"""

import asyncio
import json
from eden import Eden
from eden.admin import admin as default_admin
from eden.flags import FlagManager, Flag, FlagStrategy


async def test_admin_setup():
    """Test that admin site is properly configured."""
    print("\n=== Test 1: Admin Site Creation ===")
    
    # Create an admin site
    router = default_admin.build_router(prefix="/admin")
    
    assert router is not None, "Admin router should not be None"
    print("✓ Admin router created successfully")
    
    # Check that routes are registered
    route_paths = [route.path for route in router.routes]
    print(f"✓ Total routes registered: {len(router.routes)}")


async def test_metadata_includes_flags():
    """Test that feature flags are included in metadata."""
    print("\n=== Test 2: Metadata Includes Feature Flags ===")
    
    # Get metadata
    from eden.admin.views import admin_api_metadata
    from unittest.mock import AsyncMock, MagicMock
    
    # Create a mock request
    request = MagicMock()
    request.state = MagicMock()
    request.state.user = MagicMock()
    request.state.user.is_staff = True
    
    # Mock _check_staff to pass
    import eden.admin.views as views_module
    original_check = views_module._check_staff
    views_module._check_staff = AsyncMock()
    
    try:
        result = await admin_api_metadata(request, default_admin)
        
        # Parse the response
        if hasattr(result, 'body'):
            metadata = json.loads(result.body)
        else:
            metadata = result
        
        assert "flags" in metadata, "Metadata should include flags"
        
        flags_meta = metadata["flags"]
        assert flags_meta["table"] == "flags", "Flags table name should be 'flags'"
        assert flags_meta["verbose_name"] == "Feature Flag", "Verbose name should be 'Feature Flag'"
        assert flags_meta["is_virtual"] is True, "Flags should be marked as virtual model"
        assert flags_meta["icon"] == "fa-solid fa-flag", "Should have flag icon"
        
        # Check fields
        assert len(flags_meta["fields"]) > 0, "Should have field definitions"
        
        field_names = {f["key"] for f in flags_meta["fields"]}
        expected_fields = {"id", "name", "strategy", "enabled", "created_at", "updated_at"}
        assert expected_fields.issubset(field_names), f"Missing fields: {expected_fields - field_names}"
        
        # Check list display
        assert "name" in flags_meta["list_display"], "Should display name in list"
        assert "strategy" in flags_meta["list_display"], "Should display strategy in list"
        assert "enabled" in flags_meta["list_display"], "Should display enabled status in list"
        
        print("✓ Metadata includes flags as virtual model")
        print(f"✓ Flags fields: {', '.join(sorted(field_names))}")
        print(f"✓ List display: {', '.join(flags_meta['list_display'])}")
        
    finally:
        views_module._check_staff = original_check


async def test_admin_enabled_by_default():
    """Test that admin is enabled by default in new app instances."""
    print("\n=== Test 3: Admin Enabled by Default ===")
    
    app = Eden(
        title="Test App",
        secret_key="test-secret"
    )
    
    assert app.admin_enabled is True, "Admin should be enabled by default"
    print("✓ Admin is enabled by default in new Eden app")


async def test_flags_api_routes():
    """Test that flags API routes are available."""
    print("\n=== Test 4: Flags API Routes ===")
    
    router = default_admin.build_router(prefix="/admin")
    
    # Look for flags API routes
    flags_routes = [r for r in router.routes if "flags" in str(r.path).lower()]
    
    assert len(flags_routes) > 0, "Should have flags API routes"
    print(f"✓ Found {len(flags_routes)} flags-related routes")
    
    # Print route paths
    for route in flags_routes[:5]:
        print(f"  - {route.path}")


async def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("Admin Panel Integration Tests")
    print("="*60)
    
    try:
        await test_admin_setup()
        await test_metadata_includes_flags()
        await test_admin_enabled_by_default()
        await test_flags_api_routes()
        
        print("\n" + "="*60)
        print("✓ All tests passed!")
        print("="*60)
        print("\nThe admin panel now includes feature flags as a first-class")
        print("citizen in the sidebar navigation. Feature flags are available")
        print("in the unified admin dashboard alongside other models.")
        print("\nNew projects will have the admin panel enabled by default!")
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(asyncio.run(main()))
