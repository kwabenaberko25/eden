
import pytest
import uuid
from sqlalchemy.orm import Mapped
from eden.db import Model, StringField, IntField, Database, JSONField, JSONBField, EnumField
from eden.db.signals import receiver, post_save, pre_save, post_delete, pre_delete
from eden.db.validation import ValidationError, ValidationErrors, ValidatorMixin

# Mock Database for testing
@pytest.fixture(scope="module")
async def db():
    database = Database("sqlite+aiosqlite:///:memory:")
    await database.connect()
    Model._bind_db(database)
    async with database.engine.begin() as conn:
        await conn.run_sync(Model.metadata.create_all)
    yield database
    await database.disconnect()

class Product(Model):
    name: str = StringField(max_length=100)
    price: int = IntField()
    stock: int = IntField(default=0)

    async def clean(self):
        if self.price < 0:
            raise ValidationError("Price cannot be negative", field="price")
        if self.name == "Invalid":
            raise ValidationError("Name cannot be 'Invalid'")

@pytest.mark.asyncio
async def test_signal_registration(db):
    saved_instances = []

    @receiver(post_save, sender=Product)
    async def on_product_save(sender, instance, **kwargs):
        saved_instances.append(instance)

    product = Product(name="Test Product", price=100)
    await product.save()

    assert len(saved_instances) == 1
    assert saved_instances[0].id == product.id
    
    # Cleanup receiver to avoid side effects on other tests
    post_save.disconnect(on_product_save, sender=Product)

@pytest.mark.asyncio
async def test_validation_clean_method(db):
    product = Product(name="Invalid", price=100)
    
    with pytest.raises(ValidationErrors) as excinfo:
        await product.save()
    
    assert "__all__" in excinfo.value.errors
    assert "Name cannot be 'Invalid'" in excinfo.value.errors["__all__"]

    product.name = "Valid"
    product.price = -10
    
    with pytest.raises(ValidationErrors) as excinfo:
        await product.save()
        
    assert "price" in excinfo.value.errors
    assert "Price cannot be negative" in excinfo.value.errors["price"]

@pytest.mark.asyncio
async def test_full_clean_lifecycle(db):
    product = Product(name="A" * 101, price=10) # Too long
    
    with pytest.raises(ValidationErrors) as excinfo:
        await product.save()
    
    # Note: min_length/max_length rules are usually added by ValidationScanner 
    # from docstrings or field metadata in __init_subclass__
    # Let's verify our product has those rules.
    assert "name" in Product._validation_rules
    assert any(r.rule_type == 'max_length' for r in Product._validation_rules["name"])

@pytest.mark.asyncio
async def test_update_or_create(db):
    # Create
    product, created = await Product.update_or_create(
        name="Unique Product",
        defaults={"price": 50}
    )
    assert created is True
    assert product.price == 50

    # Update
    product_updated, created = await Product.update_or_create(
        name="Unique Product",
        defaults={"price": 75}
    )
    assert created is False
    assert product_updated.id == product.id
    assert product_updated.price == 75

@pytest.mark.asyncio
async def test_delete_signals(db):
    deleted_calls = []

    @receiver(pre_delete, sender=Product)
    async def on_product_pre_delete(sender, instance, **kwargs):
        deleted_calls.append("pre_" + str(instance.id))

    @receiver(post_delete, sender=Product)
    async def on_product_post_delete(sender, instance, **kwargs):
        deleted_calls.append("post_" + str(instance.id))

    product = await Product.create(name="To Delete", price=10)
    pid = str(product.id)
    await product.delete()

    assert f"pre_{pid}" in deleted_calls
    assert f"post_{pid}" in deleted_calls
    
    pre_delete.disconnect(on_product_pre_delete, sender=Product)
    post_delete.disconnect(on_product_post_delete, sender=Product)


@pytest.mark.asyncio
async def test_validation_inheritance(db):
    from sqlalchemy.orm import Mapped
    from eden.db import ValidatorMixin, StringField
    
    class BaseProduct(Model, ValidatorMixin):
        __abstract__ = True
        code: Mapped[str] = StringField(max_length=5)

    class SpecializedProduct(BaseProduct):
        description: Mapped[str] = StringField(max_length=10)

    # Test base constraint
    with pytest.raises(ValidationErrors) as exc:
        p = SpecializedProduct(code="TOO_LONG", description="Short")
        await p.full_clean()
    assert "code" in exc.value.errors

    # Test subclass constraint
    with pytest.raises(ValidationErrors) as exc:
        p = SpecializedProduct(code="ABC", description="DESCRIPTION_IS_TOO_LONG")
        await p.full_clean()
    assert "description" in exc.value.errors


from enum import Enum
class Status(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"

class MaturityAdvancedModel(Model, ValidatorMixin):
    tags: Mapped[list[str]] = JSONField(default=list)
    status: Mapped[Status] = EnumField(Status)
    extra_info: Mapped[dict] = JSONBField()

@pytest.mark.asyncio
async def test_fields_extended(db):
    m = MaturityAdvancedModel(
        tags=["electronics", "sale"],
        status=Status.ACTIVE,
        extra_info={"source": "api"}
    )
    
    # Should clean successfully
    await m.full_clean()
    assert m.status == Status.ACTIVE
    assert m.tags == ["electronics", "sale"]


@pytest.mark.asyncio
async def test_bulk_signals(db):
    from eden.db.signals import pre_bulk_update, post_bulk_update, pre_bulk_delete, post_bulk_delete
    
    events = []
    
    @receiver(pre_bulk_update, sender=Product)
    async def on_pre_bulk_update(sender, instance, **kwargs):
        events.append(("pre_update", kwargs.get("values")))

    @receiver(post_bulk_update, sender=Product)
    async def on_post_bulk_update(sender, instance, **kwargs):
        events.append(("post_update", kwargs.get("count")))

    @receiver(pre_bulk_delete, sender=Product)
    async def on_pre_bulk_delete(sender, instance, **kwargs):
        events.append(("pre_delete", None))

    @receiver(post_bulk_delete, sender=Product)
    async def on_post_bulk_delete(sender, instance, **kwargs):
        events.append(("post_delete", kwargs.get("count")))

    # Prepare data
    await Product.bulk_create([
        Product(name="P1", price=10),
        Product(name="P2", price=20)
    ])
    
    # Test Bulk Update
    await Product.filter(price__lt=30).update(price=100)
    
    assert any(e[0] == "pre_update" and e[1] == {"price": 100} for e in events)
    assert any(e[0] == "post_update" and e[1] >= 2 for e in events)
    
    # Test Bulk Delete
    count = await Product.filter(price=100).delete(hard=True)
    
    assert any(e[0] == "pre_delete" for e in events)
    assert any(e[0] == "post_delete" and e[1] == count for e in events)

    # Cleanup
    pre_bulk_update.disconnect(on_pre_bulk_update, sender=Product)
    post_bulk_update.disconnect(on_post_bulk_update, sender=Product)
    pre_bulk_delete.disconnect(on_pre_bulk_delete, sender=Product)
    post_bulk_delete.disconnect(on_post_bulk_delete, sender=Product)
