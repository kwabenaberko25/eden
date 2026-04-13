
import asyncio
from eden import App, Router, HttpException
from eden.requests import Request
from eden.admin.auth import AdminAuthManager, AdminRole
from eden.admin.auth_routes import get_protected_admin_routes
from eden.flags import get_flag_manager
import httpx

async def reproduce():
    app = App()
    auth = AdminAuthManager(secret_key="test-secret")
    # Register an editor
    auth.register_user("editor", "Password123!", AdminRole.EDITOR)
    
    # Setup protected routes
    router = get_protected_admin_routes(auth)
    app.include_router(router)
    
    # Mock server start/call
    # We can't easily start a full server here, but we can inspect the router paths
    print("--- Router Paths ---")
    for route in router.routes:
        print(f"{route.path} [{route.methods}]")

    # Simulate the call the JS makes: POST /admin/api/flags
    # The routes in auth_routes.py are:
    # /admin/api/flags/ (stats)
    # /admin/api/flags/flags (list/create)
    
    print("\n--- Testing API Consistency ---")
    # If JS uses api_base = "/admin/api", it calls "/admin/api/flags"
    # But the route is "/admin/api/flags/flags"
    
if __name__ == "__main__":
    asyncio.run(reproduce())
