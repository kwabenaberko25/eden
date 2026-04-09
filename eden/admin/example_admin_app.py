"""
Complete example: Using the Eden Admin Dashboard in a FastAPI app.

This shows a minimal production-ready setup.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager

# Eden imports
from eden.admin.dashboard_routes import get_admin_routes
from eden.flags import FlagsManager


# ============================================================
# Setup
# ============================================================

# Initialize flags manager
flags = FlagsManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """App lifecycle."""
    # Startup
    print("🚩 Eden Admin Dashboard ready at /admin")
    print("📊 API endpoints at /admin/flags/*")
    yield
    # Shutdown
    print("Shutting down...")


app = FastAPI(
    title="Eden Framework",
    description="Feature management with admin dashboard",
    lifespan=lifespan
)

# CORS for admin panel
app.add_middleware(
    CORSMiddleware,
    allow_origins=["localhost", "127.0.0.1"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# Admin Dashboard Routes
# ============================================================

app.include_router(get_admin_routes(prefix="/admin"))


# ============================================================
# Example: Main API
# ============================================================

@app.get("/")
async def home():
    """Homepage with link to admin."""
    return {
        "message": "Eden Framework API",
        "admin_dashboard": "/admin",
        "docs": "/docs",
        "admin_api": "/admin/flags"
    }


@app.get("/api/feature-check/{feature_id}")
async def check_feature(feature_id: str, request: Request):
    """
    Example endpoint: Check if a feature is enabled for this user.
    
    Usage:
        GET /api/feature-check/new_dashboard
    """
    try:
        is_enabled = flags.is_enabled(
            feature_id,
            request=request,  # Contextual evaluation
        )
        return {
            "feature": feature_id,
            "enabled": is_enabled,
        }
    except Exception as e:
        return {
            "error": str(e),
            "enabled": False,
        }


@app.get("/api/features")
async def get_features(request: Request):
    """
    Example endpoint: Get all features for this user.
    
    Usage:
        GET /api/features
    """
    try:
        all_features = flags.get_all_flags()
        user_features = {}
        
        for flag_id in all_features:
            user_features[flag_id] = flags.is_enabled(flag_id, request=request)
        
        return {
            "features": user_features,
            "count": len(user_features),
        }
    except Exception as e:
        return {
            "error": str(e),
            "features": {},
        }


# ============================================================
# Run
# ============================================================

if __name__ == "__main__":
    import uvicorn
    
    print("""
    ╔════════════════════════════════════════════════════════╗
    ║          Eden Admin Dashboard Example                 ║
    ╠════════════════════════════════════════════════════════╣
    ║  Dashboard:  http://localhost:8000/admin              ║
    ║  API Docs:   http://localhost:8000/docs               ║
    ║  Home:       http://localhost:8000/                   ║
    ╚════════════════════════════════════════════════════════╝
    """)
    
    uvicorn.run(
        "example_admin_app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
