"""
Complete example: Admin Dashboard with Authentication

Shows how to set up the admin dashboard with full authentication,
authorization, and user management.

Run:
    python -m uvicorn eden.admin.example_auth_app:app --reload

Then visit:
    http://localhost:8000/admin/login
    
Default users:
    admin:admin (full access)
    editor:editor (create/edit/disable flags)
    viewer:viewer (read-only access)
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from eden.admin.auth import AdminAuthManager, AdminRole
from eden.admin.auth_routes import get_protected_admin_routes


# ============================================================
# Initialization
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """App lifecycle."""
    print("""
    ╔════════════════════════════════════════════════════════╗
    ║   Eden Admin Dashboard with Authentication            ║
    ╠════════════════════════════════════════════════════════╣
    ║  Login:     http://localhost:8000/admin/login         ║
    ║  Dashboard: http://localhost:8000/admin               ║
    ║                                                        ║
    ║  Default Credentials:                                 ║
    ║  • admin:admin     (ADMIN - full access)             ║
    ║  • editor:editor   (EDITOR - create/edit flags)      ║
    ║  • viewer:viewer   (VIEWER - read-only)              ║
    ╚════════════════════════════════════════════════════════╝
    """)
    yield
    print("Shutting down...")


app = FastAPI(
    title="Eden Admin Dashboard",
    description="Authenticated feature flags management",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["localhost", "127.0.0.1"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# Authentication Setup
# ============================================================

# Create auth manager with a strong secret key
# In production, load from environment variable
SECRET_KEY = "super-secret-key-change-in-production"
auth = AdminAuthManager(
    secret_key=SECRET_KEY,
    token_expiry_hours=24,
    max_login_attempts=5,
)

# Register default users
auth.register_user("admin", "admin", AdminRole.ADMIN)
auth.register_user("editor", "editor", AdminRole.EDITOR)
auth.register_user("viewer", "viewer", AdminRole.VIEWER)

# Add protected admin routes
app.include_router(get_protected_admin_routes(auth))


# ============================================================
# Example API Endpoints
# ============================================================

@app.get("/")
async def home():
    """Home page with links."""
    return {
        "message": "Eden Admin Dashboard",
        "endpoints": {
            "login": "/admin/login",
            "dashboard": "/admin",
            "docs": "/docs",
        },
        "default_users": {
            "admin": {"username": "admin", "password": "admin", "role": "ADMIN"},
            "editor": {"username": "editor", "password": "editor", "role": "EDITOR"},
            "viewer": {"username": "viewer", "password": "viewer", "role": "VIEWER"},
        }
    }


@app.get("/health")
async def health():
    """Health check."""
    return {
        "status": "healthy",
        "authenticated_users": len([u for u in auth.list_users() if u.is_active]),
        "active_sessions": sum(1 for s in auth.sessions.values() if not s.is_expired()),
    }


# ============================================================
# Run
# ============================================================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "eden.admin.example_auth_app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
