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

from eden.admin import admin as admin_site


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
# Authentication & Admin Setup
# ============================================================

from eden.admin import admin as admin_site
from eden.auth.models import User
from eden.db import Model

# Register example models if any
# admin_site.register(MyModel)

# The AdminSite.build_router() now includes all native auth routes
admin_router = admin_site.build_router(prefix="/admin")
app.include_router(admin_router)


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
        "admin_prefix": "/admin"
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
