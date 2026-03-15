from eden import Router

inventory_router = Router()

@inventory_router.get("/")
async def index():
    """
    Index endpoint for inventory.
    """
    return {"message": "Hello from inventory router! 🌿"}
