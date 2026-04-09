"""
Test suite for Eden Admin Dashboard.

Verifies:
1. Dashboard template generates valid HTML
2. Routes are properly configured
3. API endpoints work correctly
"""

import pytest
import json
from httpx import AsyncClient, ASGITransport
from eden import Eden

from eden.admin.dashboard_template import AdminDashboardTemplate
from eden.admin.dashboard_routes import get_admin_routes
from eden.flags import FlagManager, Flag, FlagStrategy


def test_dashboard_template_renders():
    """Test that dashboard template generates HTML."""
    html = AdminDashboardTemplate.render()
    
    # Should generate HTML
    assert html.startswith("<!DOCTYPE html>")
    assert "<html lang=\"en\">" in html
    assert "</html>" in html
    
    # Should include key components
    assert "Feature Flags Admin" in html
    assert '<script>' in html
    assert '<style>' in html
    assert "getElementById" in html  # JavaScript


def test_dashboard_template_custom_params():
    """Test dashboard template with custom parameters."""
    html = AdminDashboardTemplate.render(
        api_base="/custom/flags",
        app_name="My App"
    )
    
    assert "My App" in html
    assert "/custom/flags" in html


def test_dashboard_html_structure():
    """Test that HTML has proper structure."""
    html = AdminDashboardTemplate.render()
    
    # Check for required sections
    assert "<header>" in html
    assert "Feature Flags Admin" in html
    assert "<main>" in html
    assert 'id="statsContainer"' in html
    assert 'id="flagsTable"' in html
    assert 'id="flagModal"' in html
    
    # Check for CSS
    assert "background: linear-gradient" in html
    assert ".badge-enabled" in html
    assert ".badge-disabled" in html
    
    # Check for JavaScript functions or handlers
    assert "async function loadFlags()" in html or "loadFlags" in html
    assert "saveFlag" in html or "save" in html.lower()
    assert "delete" in html.lower()  # Check for delete functionality


def test_dashboard_css_is_embedded():
    """Test that all CSS is embedded (no CDN)."""
    html = AdminDashboardTemplate.render()
    
    # Should NOT have CDN links
    assert "cdn.jsdelivr.net" not in html
    assert "bootstrap.css" not in html
    assert "cdnjs.cloudflare.com" not in html
    
    # Should have embedded styles
    assert "<style>" in html
    assert "box-sizing: border-box;" in html


def test_dashboard_js_is_embedded():
    """Test that all JavaScript is embedded."""
    html = AdminDashboardTemplate.render()
    
    # Should NOT have external libraries
    assert "jquery" not in html.lower()
    assert "cdn.jsdelivr.net" not in html
    
    # Should have vanilla JavaScript
    assert "document.addEventListener" in html
    assert "fetch(" in html
    assert "JSON.stringify" in html


@pytest.fixture
async def app_with_admin():
    """Create Eden app with admin dashboard."""
    app = Eden(secret_key="test-secret-key-long-enough-for-jwt")
    app.include_router(get_admin_routes(prefix="/admin"))
    return await app.build()


@pytest.fixture
async def client(app_with_admin):
    """Create async test client."""
    transport = ASGITransport(app=app_with_admin)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c



@pytest.mark.asyncio
async def test_admin_dashboard_route(client):
    """Test that dashboard route returns HTML."""
    response = await client.get("/admin/")
    
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "Feature Flags Admin" in response.text


@pytest.mark.asyncio
async def test_admin_dashboard_alias_route(client):
    """Test that dashboard alias route works."""
    response = await client.get("/admin/dashboard")
    
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")


@pytest.mark.asyncio
async def test_flags_list_endpoint(client):
    """Test GET /admin/flags endpoint."""
    response = await client.get("/admin/flags")
    
    # Should return JSON list
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_flags_stats_endpoint(client):
    """Test GET /admin/flags/ stats endpoint."""
    response = await client.get("/admin/flags/")
    
    # Should return stats
    assert response.status_code == 200
    data = response.json()
    assert "total_flags" in data
    assert "enabled_flags" in data
    assert "disabled_flags" in data


@pytest.mark.asyncio
async def test_create_flag_endpoint(client):
    """Test POST /admin/flags for creating a flag."""
    flag_data = {
        "name": "Test Flag",
        "description": "Test description",
        "strategy": "always_on",
        "enabled": True
    }
    
    response = await client.post("/admin/flags", json=flag_data)
    
    # Should create flag
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Flag"
    assert data["strategy"] == "always_on"


@pytest.mark.asyncio
async def test_get_flag_endpoint(client):
    """Test GET /admin/flags/{flag_id}."""
    # First create a flag
    flag_data = {
        "name": "Get Test",
        "strategy": "always_off",
        "enabled": False
    }
    create_resp = await client.post("/admin/flags", json=flag_data)
    flag_id = create_resp.json()["id"]
    
    # Then get it
    response = await client.get(f"/admin/flags/{flag_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == flag_id
    assert data["enabled"] == False


@pytest.mark.asyncio
async def test_update_flag_endpoint(client):
    """Test PATCH /admin/flags/{flag_id}."""
    # Create flag
    flag_data = {
        "name": "Update Test",
        "strategy": "percentage",
        "percentage": 25,
        "enabled": True
    }
    create_resp = await client.post("/admin/flags", json=flag_data)
    flag_id = create_resp.json()["id"]
    
    # Update it
    update_data = {
        "percentage": 75,
        "enabled": False
    }
    response = await client.patch(f"/admin/flags/{flag_id}", json=update_data)
    
    assert response.status_code == 200
    data = response.json()
    assert data["percentage"] == 75
    assert data["enabled"] == False


@pytest.mark.asyncio
async def test_delete_flag_endpoint(client):
    """Test DELETE /admin/flags/{flag_id}."""
    # Create flag
    flag_data = {
        "name": "Delete Test",
        "strategy": "always_on"
    }
    create_resp = await client.post("/admin/flags", json=flag_data)
    flag_id = create_resp.json()["id"]
    
    # Delete it
    response = await client.delete(f"/admin/flags/{flag_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "deleted"


def test_dashboard_html_no_internet_required():
    """Test that dashboard HTML has no external dependencies."""
    html = AdminDashboardTemplate.render()
    
    # Should not reference any external resources
    forbidden_patterns = [
        "http://cdn",
        "https://cdn",
        "@import url",
        "script src=",  # External scripts (except data URLs)
    ]
    
    for pattern in forbidden_patterns:
        # Allow script src for internal data, but not URLs
        if pattern == "script src=":
            # Check that there are no http/https src attributes
            assert 'src="http' not in html
            assert "src='http" not in html
        else:
            assert pattern not in html


def test_dashboard_responsiveness():
    """Test that dashboard includes responsive design."""
    html = AdminDashboardTemplate.render()
    
    # Should have viewport meta tag for mobile
    assert 'name="viewport"' in html
    assert "width=device-width" in html
    
    # Should have responsive CSS
    assert "@media" in html or "flex" in html or "grid" in html
    assert "grid-template-columns: repeat(auto-fit" in html


def test_dashboard_accessibility():
    """Test basic accessibility features."""
    html = AdminDashboardTemplate.render()
    
    # Should have proper language tag
    assert 'lang="en"' in html
    
    # Should have meta charset
    assert 'charset="UTF-8"' in html
    
    # Should have title
    assert "<title>" in html
    
    # Form elements should have labels
    assert "<label>" in html


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
