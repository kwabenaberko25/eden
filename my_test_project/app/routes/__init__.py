from eden import Router
from eden.responses import html

main_router = Router()

@main_router.get("/")
async def index():
    return html("<html><body><h1>Auto-Reloaded Programmatic Reload to my_test_project! 🌿</h1></body></html>")

@main_router.get("/health")
async def health():
    return {"status": "healthy"}
