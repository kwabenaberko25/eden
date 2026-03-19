
import pytest
from eden.app import Eden
from eden.messages import get_messages
from eden.requests import Request
from starlette.datastructures import Headers
from starlette.middleware.sessions import SessionMiddleware

@pytest.mark.asyncio
async def test_eden_toasts_directive():
    app = Eden(secret_key="secret")
    # Manually add session and messages middleware since they are disabled in tests by default
    app.add_middleware("session", secret_key="secret")
    app.add_middleware("messages")
    
    # Register a route to test rendering
    @app.get("/add-and-render")
    async def add_and_render(request: Request):
        from eden.responses import html
        msgs = get_messages(request)
        msgs.info("Hello World")
        # Use env.from_string as EdenTemplates is a wrapper
        rendered = app.templates.env.from_string("@eden_toasts").render({"request": request})
        return html(rendered)

    from starlette.testclient import TestClient
    # Ensure app is built
    await app.build()
    client = TestClient(app)
    
    response = client.get("/add-and-render")
    assert response.status_code == 200
    assert "eden-toast-container" in response.text
    assert "showToast" in response.text
    assert "Hello World" in response.text
    assert "info" in response.text

@pytest.mark.asyncio
async def test_eden_scripts_websocket_integration():
    app = Eden()
    
    # Verify eden_scripts contains the WebSocket connection logic
    @app.get("/scripts")
    async def scripts(request: Request):
        from eden.responses import html
        rendered = app.templates.env.from_string("@eden_scripts").render({"request": request})
        return html(rendered)

    from starlette.testclient import TestClient
    await app.build()
    client = TestClient(app)
    response = client.get("/scripts")
    assert response.status_code == 200
    assert "/_eden/sync" in response.text
    assert "new WebSocket" in response.text
    assert "eden:message" in response.text
