import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from eden.admin import admin, ModelAdmin, TabularInline
from eden.db import Model, StringField, IntField
from eden.requests import Request
from eden.responses import HtmlResponse
import uuid

# Define test models
class AdminCategory(Model):
    __tablename__ = "test_categories"
    id = IntField(primary_key=True)
    name = StringField(max_length=100)

class AdminProduct(Model):
    __tablename__ = "test_products"
    id = IntField(primary_key=True)
    name = StringField(max_length=100)
    category_id = IntField()

class AdminProductInline(TabularInline):
    model = AdminProduct
    extra = 2

class AdminCategoryAdmin(ModelAdmin):
    list_display = ["id", "name"]
    inlines = [AdminProductInline]
    verbose_name = "Category"

@pytest.mark.asyncio
async def test_admin_add_view():
    """Test that the add view renders and processes data.
    
    The admin views rely on admin_site.templates.TemplateResponse which 
    invokes Jinja2 rendering with url_for(), requiring a full ASGI app context.
    We mock the TemplateResponse to isolate the view logic.
    """
    from eden.admin.views import admin_add_view

    # Build request with proper state
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/admin/test_categories/add",
        "headers": [],
        "query_string": b"",
        "state": {"user": type("User", (), {"id": uuid.uuid4(), "is_staff": True})()}
    }
    request = Request(scope)
    
    # Create admin site and mock the template rendering
    ma = AdminCategoryAdmin()
    mock_admin = MagicMock()
    mock_admin._registry = {}
    
    mock_response = HtmlResponse(content="<h1>Add Category</h1>", status_code=200)
    mock_admin.templates = MagicMock()
    mock_admin.templates.TemplateResponse = MagicMock(return_value=mock_response)

    response = await admin_add_view(request, AdminCategory, ma, mock_admin)
    assert response.status_code == 200
    assert b"Add Category" in response.body
    
    # Verify TemplateResponse was called with correct template and context
    mock_admin.templates.TemplateResponse.assert_called_once()
    call_args = mock_admin.templates.TemplateResponse.call_args
    assert call_args[0][1] == "form.html"  # template name
    assert call_args[0][2]["is_add"] is True
    assert call_args[0][2]["model_name"] == "Category"

@pytest.mark.asyncio
async def test_admin_edit_view_logic():
    """Test the edit view logic (GET).
    
    Uses a mock admin_site with mocked TemplateResponse to avoid 
    requiring a full ASGI app context.
    """
    from eden.admin.views import admin_edit_view

    # Create an instance
    cat = AdminCategory(id=1, name="Electronics")
    
    # Mock the 'get' method on the model
    async def mock_get(session, record_id):
        if str(record_id) == "1":
            return cat
        return None
    
    AdminCategory.get = mock_get
    
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/admin/test_categories/1/edit",
        "headers": [],
        "query_string": b"",
        "state": {"user": type("User", (), {"id": uuid.uuid4(), "is_staff": True})()}
    }
    request = Request(scope)
    
    ma = AdminCategoryAdmin()
    mock_admin = MagicMock()
    mock_admin._registry = {}
    
    mock_response = HtmlResponse(content="<h1>Edit Category</h1><p>Electronics</p>", status_code=200)
    mock_admin.templates = MagicMock()
    mock_admin.templates.TemplateResponse = MagicMock(return_value=mock_response)

    response = await admin_edit_view(request, AdminCategory, ma, "1", mock_admin)
    assert response.status_code == 200
    assert b"Edit Category" in response.body
    assert b"Electronics" in response.body
    
    # Verify TemplateResponse was called with correct context
    mock_admin.templates.TemplateResponse.assert_called_once()
    call_args = mock_admin.templates.TemplateResponse.call_args
    assert call_args[0][1] == "form.html"  # template name
    assert call_args[0][2]["is_add"] is False
    assert call_args[0][2]["record"] is cat
