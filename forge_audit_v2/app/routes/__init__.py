from eden import Router
from .inventory import inventory_router

main_router = Router()

@main_router.get("/")
async def index():
    return {"message": "Welcome to forge_audit_v2! 🌿"}

@main_router.get("/health")
async def health():
    return {"status": "healthy"}

main_router.include_router(inventory_router)
