import hmac
import hashlib
import json
import pytest
from httpx import AsyncClient, ASGITransport
from eden.app import Eden
from eden.components import Component, register, action

@register("secure_test")
class SecureComponent(Component):
    template_name = "test.html"
    
    def __init__(self, count=0, **kwargs):
        self.count = int(count)
        super().__init__(**kwargs)
    
    @action
    async def increment(self, request):
        self.count += 1
        return f"Count is {self.count}"

def test_component_signature_verification():
    app = Eden(debug=True, secret_key="super-secret")
    
    @app.get("/")
    async def index(request):
        comp = SecureComponent(count=10)
        return await comp.render()

    client = TestClient(app)
    
    # 1. Get the legitimate state and signature
    # (In a real app, this is rendered into the HTML)
    comp = SecureComponent(count=10)
    state = comp.get_state()
    
    # Eden's canonicalization: stringify all non-None values
    canonical = {str(k): str(v) for k, v in state.items() if v is not None}
    state_json = json.dumps(canonical, sort_keys=True)
    
    signature = hmac.new(
        b"super-secret",
        state_json.encode(),
        hashlib.sha256
    ).hexdigest()
    
    # 2. Valid request - Should pass
    response = client.post(
        "/_eden/component/secure_test/increment",
        data=state,
        headers={"X-Eden-State-Signature": signature}
    )
    assert response.status_code == 200
    assert "Count is 11" in response.text
    
    # 3. Tampered state - Should fail (count changed but signature same)
    tampered_state = state.copy()
    tampered_state["count"] = 999
    response = client.post(
        "/_eden/component/secure_test/increment",
        data=tampered_state,
        headers={"X-Eden-State-Signature": signature}
    )
    assert response.status_code == 403
    assert "Invalid component state signature" in response.text

    # 4. Missing signature - Should fail
    response = client.post(
        "/_eden/component/secure_test/increment",
        data=state
    )
    assert response.status_code == 403

if __name__ == "__main__":
    test_component_signature_verification()
    print("✅ HMAC Security Verification Passed!")
