
import pytest
from unittest.mock import Mock, MagicMock
from eden.templating.templates import EdenTemplates, render_fragment
from starlette.requests import Request
from starlette.datastructures import Headers

@pytest.fixture
def mock_env():
    env = MagicMock()
    # Mock template and its blocks
    tmpl = MagicMock()
    tmpl.blocks = {"fragment_user_list": lambda ctx: ["<li>User 1</li>"]}
    env.get_template.return_value = tmpl
    return env

@pytest.fixture
def templates(mock_env):
    # Initialize with mock environment
    obj = EdenTemplates(directory="templates")
    obj.env = mock_env
    return obj

def test_smart_fragment_resolution_active(templates):
    """Test that HTMX request with matching target resolves correctly."""
    # Mock HTMX request targeting "user-list"
    scope = {
        "type": "http",
        "headers": [(b"hx-request", b"true"), (b"hx-target", b"user-list")]
    }
    request = Request(scope=scope)
    
    context = {"request": request}
    
    # We expect TemplateResponse to detect hx-target="user-list"
    # and call render_fragment with "user_list"
    response = templates.TemplateResponse("index.html", context)
    
    assert response.body == b"<li>User 1</li>"
    assert response.headers["content-type"] == "text/html; charset=utf-8"

def test_explicit_fragment_override(templates):
    """Test that __fragment__ in context takes precedence."""
    scope = {
        "type": "http",
        "headers": [(b"hx-request", b"true"), (b"hx-target", b"wrong-target")]
    }
    request = Request(scope=scope)
    
    # Explicitly request "user-list" fragment despite HX-Target
    context = {"request": request, "__fragment__": "user-list"}
    
    response = templates.TemplateResponse("index.html", context)
    
    assert response.body == b"<li>User 1</li>"

def test_fallback_to_full_render_if_fragment_missing(templates):
    """Test that missing fragment falls back to full render."""
    scope = {
        "type": "http",
        "headers": [(b"hx-request", b"true"), (b"hx-target", b"non-existent")]
    }
    request = Request(scope=scope)
    
    context = {"request": request}
    
    # We need to mock super().TemplateResponse since we are falling back
    with MagicMock() as mock_super:
        templates.__class__.__bases__[0].TemplateResponse = mock_super
        templates.TemplateResponse("index.html", context)
        assert mock_super.called

def test_no_htmx_full_render(templates):
    """Test that non-HTMX request renders full page."""
    scope = {
        "type": "http",
        "headers": []
    }
    request = Request(scope=scope)
    
    context = {"request": request}
    
    with MagicMock() as mock_super:
        templates.__class__.__bases__[0].TemplateResponse = mock_super
        templates.TemplateResponse("index.html", context)
        assert mock_super.called
