from eden.app import Eden
from eden.requests import Request
from eden.responses import JsonResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.testclient import TestClient
import os

app = Eden(secret_key="test-secret", debug=True)

@app.get("/error403")
async def error403():
    # Raise a 403 exception
    raise StarletteHTTPException(status_code=403, detail="Forbidden area")

def test_debug_page_status_code():
    client = TestClient(app)
    # Get the HTML debug page by specifying Accept header
    response = client.get("/error403", headers={"Accept": "text/html"})
    
    # Check if the title/icon/etc is correct
    assert response.status_code == 403
    assert "Forbidden" in response.text
    # Icon checking (status icon for 403 is 🚫)
    # The debug page icon is rendered based on status code
    assert "🚫" in response.text
    print("\nVerified: Debug page status code is dynamic (403).")

if __name__ == "__main__":
    test_debug_page_status_code()
