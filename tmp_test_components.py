import asyncio
import os
from typing import Any, Optional
from starlette.testclient import TestClient
from eden.app import Eden
from eden.components import Component, register, action
from eden.responses import HtmlResponse

# Ensure templates directory exists for the test
os.makedirs("templates/components", exist_ok=True)

# Define and register the component
@register("counter")
class Counter(Component):
    template_name = "components/counter.html"
    count: int = 0
    id: str = "1"

    @action
    def increment(self, request):
        # State is passed via __init__ called by dispatcher
        self.count = int(self.count) + 1
        return self # Renders itself

async def main():
    # Initialize Eden with the local templates directory
    app = Eden(debug=True)
    
    @app.get("/")
    async def index(request):
        return request.render("index.html")

    # Build the app (Required for component router to be included)
    starlette_app = await app.build()
    client = TestClient(starlette_app)

    print("--- Starting Component Tests ---")

    # 1. Test Initial Rendering
    print("\n[1] Testing initial rendering...")
    response = client.get("/")
    print(f"Status: {response.status_code}")
    # print(f"Content: {response.text}")
    assert response.status_code == 200
    assert "Count: 5" in response.text
    assert 'hx-post="/_eden/component/counter/increment"' in response.text
    print("✓ Initial rendering passed")

    # 2. Test Action POST
    print("\n[2] Testing action POST (increment)...")
    # Simulate HTMX POST with state
    # The dispatcher will call Counter(count=10, id='test') then .increment()
    response = client.post("/_eden/component/counter/increment", data={"count": 10, "id": "test"})
    print(f"Status: {response.status_code}")
    print(f"Content: {response.text}")
    assert response.status_code == 200
    assert "Count: 11" in response.text
    assert 'id="counter-test"' in response.text
    print("✓ Action POST passed")

    # 3. Test Action GET
    print("\n[3] Testing action GET (increment)...")
    response = client.get("/_eden/component/counter/increment?count=20&id=test2")
    print(f"Status: {response.status_code}")
    print(f"Content: {response.text}")
    assert response.status_code == 200
    assert "Count: 21" in response.text
    assert 'id="counter-test2"' in response.text
    print("✓ Action GET passed")

    print("\n--- All component tests passed! ---")

if __name__ == "__main__":
    asyncio.run(main())
