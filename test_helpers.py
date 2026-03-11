import sys
import os
import asyncio
from typing import Mapping

# Add the current directory to sys.path to import eden
sys.path.append(os.getcwd())

from eden.forms import Schema, field, v
from eden.requests import Request
from eden.app import Eden

async def test_form_helpers():
    print("Testing form helpers...")
    
    class TestSchema(Schema):
        name: str = field(label="Name", widget="text", pattern="^[A-Za-z]+$")
        email: str = v(label="Email", widget="email")
    
    # Check field metadata
    name_field = TestSchema.model_fields["name"]
    email_field = TestSchema.model_fields["email"]

    # Check that pattern was saved in json_schema_extra
    assert name_field.json_schema_extra.get("pattern") == "^[A-Za-z]+$"
    
    print(f"Name field label: {name_field.json_schema_extra.get('label')}")
    print(f"Email field label: {email_field.json_schema_extra.get('label')}")
    
    assert name_field.json_schema_extra.get("label") == "Name"
    assert email_field.json_schema_extra.get("label") == "Email"
    assert name_field.json_schema_extra.get("widget") == "text"
    assert email_field.json_schema_extra.get("widget") == "email"

    # Verify Pydantic validation uses the pattern natively
    try:
        TestSchema(name="123", email="test@test.com")
        assert False, "Should have failed pattern validation"
    except Exception as e:
        assert "String should match pattern" in str(e)
    
    print("Form helpers test passed!")

async def test_request_render():
    print("\nTesting request.render()...")
    
    app = Eden()
    # Mock scope
    scope = {
        "type": "http",
        "eden_app": app,
        "app": app
    }
    
    request = Request(scope)
    
    # Ensure request.app returns the eden app
    assert request.app == app
    
    # Mock app.eden.render
    class MockEden:
        def render(self, template_name, context=None, **kwargs):
            return f"Rendered {template_name} with {context} and {kwargs}"
    
    app.eden = MockEden()
    
    result = request.render("test.html", {"foo": "bar"}, baz="qux")
    print(f"Render result: {result}")
    
    assert "test.html" in result
    assert "{'foo': 'bar'}" in result
    assert "{'baz': 'qux'}" in result
    
    print("request.render() test passed!")

async def test_named_routes():
    print("\nTesting named routes...")
    from eden.routing import Router
    from eden.app import Eden
    
    app = Eden()
    users_router = Router(name="users", prefix="/users")
    
    @users_router.get("/new", name="new_user")
    async def new_user(request):
        pass
        
    app.include_router(users_router)
    
    # Verify the route was named correctly
    routes = app.get_routes()
    matches = [r for r in routes if r["name"] == "users:new_user"]
    assert len(matches) == 1
    print("Named routes test passed!")

async def test_template_url():
    print("\nTesting @url directive...")
    from eden.templating import EdenDirectivesExtension
    
    ext = EdenDirectivesExtension(None)
    source = 'Click <a href="@url("users:new_user", id=1)">Here</a>'
    processed = ext.preprocess(source, None)
    
    assert '{{ url_for("users:new_user", id=1) }}' in processed
    print("@url directive test passed!")

if __name__ == "__main__":
    asyncio.run(test_form_helpers())
    asyncio.run(test_request_render())
    asyncio.run(test_named_routes())
    asyncio.run(test_template_url())
