import pytest
import os
import shutil
import tempfile
from unittest.mock import patch
from starlette.testclient import TestClient
from eden.app import Eden
from eden.components import Component, action, _action_registry, register
from eden.templating import EdenTemplates

class MockUserComponent(Component):
    @action("user-greet")
    def greet(self, request, **kwargs):
        name = kwargs.get("name", "World")
        return f"Hello, {name}!"

    @action("user-add")
    async def add(self, request, **kwargs):
        a = kwargs.get("a", 0)
        b = kwargs.get("b", 0)
        return f"Result: {int(a) + int(b)}"

def test_component_registry():
    # Registration happens via decorator when using @register
    register("mock-user")(MockUserComponent)
    
    match = _action_registry.get("user-greet")
    assert match is not None
    assert match[0] == MockUserComponent
    assert match[1] == "greet"

def test_url_directive_transformation():
    # Setup template dir manually to avoid tmp_path issues
    temp_dir = tempfile.mkdtemp()
    try:
        template_dir = os.path.join(temp_dir, "templates")
        os.makedirs(template_dir)
        
        # Test file with @url shorthand
        index_file = os.path.join(template_dir, "index.html")
        with open(index_file, "w") as f:
            f.write('<button hx-post="@url(\'component:user-greet\', name=\'Eden\')">Greet</button>')
        
        templates = EdenTemplates(directory=template_dir)
        template = templates.get_template("index.html")
        
        def mock_url_for(endpoint_name, **kwargs):
            if endpoint_name == "component:dispatch":
                params = "&".join([f"{k}={v}" for k, v in kwargs.items() if k != "action_slug"])
                return f"/_components/{kwargs['action_slug']}?{params}"
            return f"/{endpoint_name}"

        rendered = template.render(url_for=mock_url_for)
        assert '/_components/user-greet?name=Eden' in rendered
    finally:
        shutil.rmtree(temp_dir)

@pytest.mark.asyncio
async def test_component_dispatcher_integration():
    register("mock-user")(MockUserComponent)
    
    app = Eden()
    # Eden.build is async
    starlette_app = await app.build()
    
    # TestClient can be used with a built Starlette app
    with TestClient(starlette_app) as client:
        # Patch signature verification to allow unsigned test requests
        with patch("eden.components.Component._verify_state_signature", return_value=True):
            # Test GET action
            response = client.get("/_components/user-greet?name=Tester")
            assert response.status_code == 200
            assert response.text == "Hello, Tester!"
            
            # Test POST action with form data
            response = client.post("/_components/user-add", data={"a": "10", "b": "20"})
            assert response.status_code == 200
            assert response.text == "Result: 30"

@pytest.mark.asyncio
async def test_component_not_found():
    app = Eden()
    starlette_app = await app.build()
    with TestClient(starlette_app) as client:
        response = client.get("/_components/non-existent-action")
        assert response.status_code == 404
        assert "not found" in response.text.lower()
