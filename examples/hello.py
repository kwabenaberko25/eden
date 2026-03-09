"""
Eden — Example application.

A minimal "Hello, Eden!" app demonstrating routes, path params,
query params, dependency injection, middleware, and error handling.

Run:
    python examples/hello.py
"""

from eden import Eden, Depends, NotFound, Request, Router

app = Eden(title="Hello Eden", debug=True)

# ── Middleware ───────────────────────────────────────────────────────────

app.add_middleware("cors", allow_origins=["*"])


# ── Dependencies ─────────────────────────────────────────────────────────


async def get_current_user():
    """Simulate a user lookup (replace with real auth in production)."""
    return {"id": 1, "name": "Eden User", "email": "user@eden.dev"}


# ── Routes ───────────────────────────────────────────────────────────────


@app.get("/")
async def index():
    """Root endpoint."""
    return {"message": "Hello, Eden! 🌿", "version": app.version}


@app.get("/greet/{name}")
async def greet(name: str):
    """Greet a user by name (path parameter)."""
    return {"greeting": f"Hello, {name}! Welcome to Eden."}


@app.get("/items/{item_id:int}")
async def get_item(item_id: int, request: Request):
    """Get an item by ID (typed path param + query params)."""
    verbose = request.get_query("verbose", "false")
    return {
        "item_id": item_id,
        "verbose": verbose == "true",
        "detail": f"Item #{item_id}" if verbose == "true" else None,
    }


@app.get("/me")
async def get_me(user=Depends(get_current_user)):
    """Get current user via dependency injection."""
    return {"user": user}


# ── Sub-Router ───────────────────────────────────────────────────────────

api = Router(prefix="/api/v1")


@api.get("/status")
async def api_status():
    return {"api": "v1", "status": "operational"}


@api.get("/users/{user_id:int}")
async def api_get_user(user_id: int):
    if user_id > 100:
        raise NotFound(detail=f"User #{user_id} not found.")
    return {"user_id": user_id, "name": f"User {user_id}"}


app.include_router(api)

# ── Custom Exception Handler ────────────────────────────────────────────


@app.exception_handler(NotFound)
async def custom_404(request: Request, exc: NotFound):
    from eden.responses import JsonResponse

    return JsonResponse(
        content={
            "error": True,
            "message": exc.detail,
            "path": str(request.url.path),
        },
        status_code=404,
    )


# ── Run ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000)
