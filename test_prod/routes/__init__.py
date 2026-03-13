"""
Application routes.
"""

from eden import Router

main_router = Router()

@main_router.get("/")
async def index():
    return {"message": "Welcome to test_prod! 🌿"}

@main_router.get("/health")
async def health():
    return {"status": "healthy"}
