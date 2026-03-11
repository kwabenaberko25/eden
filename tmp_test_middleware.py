
import asyncio
from typing import Any
from starlette.testclient import TestClient
from eden.app import Eden
from eden.requests import Request
from eden.responses import JsonResponse

# 1. Define functional middleware
async def logging_middleware(request: Request, call_next: Any):
    print(f"DEBUG: App middleware before: {request.url.path}")
    response = await call_next(request)
    response.headers["X-App-Log"] = "true"
    print(f"DEBUG: App middleware after: {request.url.path}")
    return response

async def auth_middleware(request: Request, call_next: Any):
    print(f"DEBUG: Route middleware before: {request.url.path}")
    if request.query_params.get("token") != "secret":
        return JsonResponse({"error": "Unauthorized"}, status_code=401)
    response = await call_next(request)
    response.headers["X-Route-Auth"] = "passed"
    print(f"DEBUG: Route middleware after: {request.url.path}")
    return response

# 2. Setup Eden app
app = Eden()
app.add_middleware(logging_middleware)

@app.get("/")
async def index(request: Request):
    return {"message": "Hello World"}

@app.get("/secure", middleware=[auth_middleware])
async def secure(request: Request):
    return {"message": "Secure Data"}

# 3. Run tests using TestClient
async def test_middleware():
    # Eden.build() is async
    starlette_app = await app.build()
    client = TestClient(starlette_app)
    
    # Test App-level Middleware
    print("\nTesting App Middleware...")
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello World"}
    assert response.headers["X-App-Log"] == "true"
    print("App Middleware: SUCCESS")

    # Test Route-level Middleware (Failure)
    print("\nTesting Route Middleware (Unauthorized)...")
    response = client.get("/secure")
    assert response.status_code == 401
    assert response.json() == {"error": "Unauthorized"}
    assert response.headers["X-App-Log"] == "true"
    assert "X-Route-Auth" not in response.headers
    print("Route Middleware (Failure): SUCCESS")

    # Test Route-level Middleware (Success)
    print("\nTesting Route Middleware (Authorized)...")
    response = client.get("/secure?token=secret")
    assert response.status_code == 200
    assert response.json() == {"message": "Secure Data"}
    assert response.headers["X-App-Log"] == "true"
    assert response.headers["X-Route-Auth"] == "passed"
    print("Route Middleware (Success): SUCCESS")

if __name__ == "__main__":
    asyncio.run(test_middleware())
