import pytest
import asyncio
from typing import Annotated, Optional, List, Any
import uuid
from eden.db import Model, Database, StringField, IntField, Relationship, Mapped, mapped_column, ForeignKeyField
from eden.db.metadata import MaxLength, Label, Choices, Required
from eden.forms import Schema, BaseForm, ModelForm
from eden.db.lookups import q

# 1. Define modern models
class Category(Model):
    __tablename__ = "categorys"
    __table_args__ = {"extend_existing": True}
    name: Annotated[str, MaxLength(50), Label("Category Name")]

class Product(Model):
    __tablename__ = "products"
    __table_args__ = {"extend_existing": True}
    title: Annotated[str, MaxLength(100), Label("Product Title"), Required]
    price: int = IntField(default=0)
    status: Annotated[str, Choices(["draft", "published", "archived"]), Label("Current Status")]
    category_id: Optional[uuid.UUID] = ForeignKeyField("categorys.id", nullable=True)
    
    category: Mapped[Optional[Category]] = Relationship(back_populates="products")

Category.products = Relationship(Product, back_populates="category")

@pytest.mark.asyncio
async def test_form_metadata_propagation():
    """Verify that ORM metadata flows seamlessly into forms."""
    
    # Test 1: Model.as_form()
    form = Product.as_form()
    
    # Check title field
    title_field = form["title"]
    assert title_field.label == "Product Title"
    assert title_field.required is True
    assert title_field.attributes["max_length"] == 100
    
    # Check status field
    status_field = form["status"]
    assert status_field.label == "Current Status"
    assert "choices" in status_field.attributes
    assert status_field.attributes["choices"] == ["draft", "published", "archived"]

@pytest.mark.asyncio
async def test_schema_declarative_integration():
    """Verify that Schema class can pull fields from Model correctly."""
    
    class ProductSchema(Schema):
        class Meta:
            model = Product
            include = ["title", "price"]

    # Verify Pydantic validation
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        ProductSchema(title="a" * 101, price=10) # Too long
    valid_data = {"title": "Test Product", "price": 100}
    schema_inst = ProductSchema(**valid_data)
    assert schema_inst.title == "Test Product"
    
    # Verify metadata in form created from schema
    form = ProductSchema.as_form(data=valid_data)
    assert form["title"].label == "Product Title"

@pytest.mark.asyncio
async def test_model_form_saving(db):
    """Verify that ModelForm saves data correctly to the database."""
    
    class ProductCreateForm(ModelForm):
        class Meta:
            model = Product
            fields = ["title", "price", "status"]

    data = {
        "title": "Form Saved Product",
        "price": 299,
        "status": "published"
    }
    
    form = ProductCreateForm(data=data)
    assert form.is_valid()
    
    product = await form.save()
    assert product.id is not None
    assert product.title == "Form Saved Product"
    
    # Verify we can query it back using advanced lookups
    fetched = await Product.query().filter(q.title.icontains("Saved")).first()
    assert fetched.id == product.id
    assert fetched.price == 299

@pytest.mark.asyncio
async def test_complex_query_integration(db):
    """Verify that we can use streamlined lookups with joined data."""
    cat = await Category.create(name="Electronics")
    await Product.create(title="Laptop", price=1000, category_id=cat.id, status="published")
    await Product.create(title="Phone", price=500, category_id=cat.id, status="published")
    
    # Query using attribute lookup and automatic join
    results = await Product.query().filter(Product.category.name == "Electronics").all()
    assert len(results) == 2
    assert all(p.category_id == cat.id for p in results)
    
    # Query using select_related
    p = await Product.query().filter(title="Laptop").select_related("category").first()
    assert p.category.name == "Electronics"
    
    # Query using values_list
    prices = await Product.query().order_by("price").values_list("price", flat=True)
    assert prices == [500, 1000]
