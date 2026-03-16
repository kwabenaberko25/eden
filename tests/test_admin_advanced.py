import pytest
from eden.admin import admin, ModelAdmin, TabularInline
from eden.db import Model, StringField, IntField
from eden.requests import Request
from eden.admin.views import admin_list_view, admin_add_view, admin_edit_view
import uuid

# Define test models
class Category(Model):
    __tablename__ = "test_categories"
    id = IntField(primary_key=True)
    name = StringField(max_length=100)

class Product(Model):
    __tablename__ = "test_products"
    id = IntField(primary_key=True)
    name = StringField(max_length=100)
    category_id = IntField()

class ProductInline(TabularInline):
    model = Product
    extra = 2

class CategoryAdmin(ModelAdmin):
    list_display = ["id", "name"]
    inlines = [ProductInline]

@pytest.mark.asyncio
async def test_admin_add_view():
    """Test that the add view renders and processes data."""
    # Mock request
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/admin/test_categories/add",
        "headers": [],
        "query_string": b"",
        "state": {"user": type("User", (), {"id": uuid.uuid4(), "is_staff": True})()}
    }
    request = Request(scope)
    
    # We need to register the model
    admin.register(Category, CategoryAdmin)
    ma = admin._registry[Category]
    
    response = await admin_add_view(request, Category, ma)
    assert response.status_code == 200
    assert b"Add Category" in response.body

@pytest.mark.asyncio
async def test_admin_edit_view_logic():
    """Test the edit view logic (GET)."""
    # Create an instance
    cat = Category(id=1, name="Electronics")
    # In a real test we'd save it to DB, but let's mock the 'get' method
    
    async def mock_get(session, record_id):
        if str(record_id) == "1":
            return cat
        return None
    
    Category.get = mock_get
    
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/admin/test_categories/1/edit",
        "headers": [],
        "query_string": b"",
        "state": {"user": type("User", (), {"id": uuid.uuid4(), "is_staff": True})()}
    }
    request = Request(scope)
    
    ma = CategoryAdmin()
    response = await admin_edit_view(request, Category, ma, "1")
    assert response.status_code == 200
    assert b"Edit Category" in response.body
    assert b"Electronics" in response.body
