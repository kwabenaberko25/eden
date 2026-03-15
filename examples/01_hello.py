"""
01_hello.py — The Simplest Eden App

This example shows the absolute minimum needed to run an Eden application.
No models, no database, just basic routing and JSON responses.

Run:
    python examples/01_hello.py

Then visit http://localhost:8000 in your browser.
"""

from eden import Eden

app = Eden(title="Hello Eden", debug=True)


@app.get("/")
async def hello():
    """Root endpoint - returns JSON."""
    return {"message": "Hello, Eden! 🌿"}


@app.get("/greet/{name}")
async def greet(name: str):
    """Greet a person by name (path parameter)."""
    return {"greeting": f"Hello, {name}!"}


@app.get("/items")
async def list_items(skip: int = 0, limit: int = 10):
    """Query parameters example."""
    return {
        "skip": skip,
        "limit": limit,
        "items": [f"Item {i}" for i in range(skip, skip + limit)]
    }


if __name__ == "__main__":
    # Add basic middleware
    app.add_middleware("cors", allow_origins=["*"])
    
    # Run the app
    app.run(port=8000)

# What you learned:
#   - Creating an Eden app: app = Eden(...)
#   - Decorators: @app.get(path)
#   - Path parameters: {name}
#   - Query parameters: skip, limit
#   - Returning JSON automatically
#   - Running the dev server: app.run()
#
# Next: See 02_rest_api.py to add a database and models
