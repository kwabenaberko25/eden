
import asyncio
import uuid
from sqlalchemy.orm import Mapped
from eden.db import Model, StringField, IntField, Database
from eden.db.validation import ValidationErrors

async def repro():
    database = Database("sqlite+aiosqlite:///:memory:")
    await database.connect()
    Model._bind_db(database)
    async with database.engine.begin() as conn:
        await conn.run_sync(Model.metadata.create_all)

    class MaturityProduct(Model):
        name: str = StringField(max_length=100)
        price: int = IntField()
        stock: int = IntField(default=0)

    # Test logic for _has_default
    def has_default(model_cls, name):
        attr = getattr(model_cls, name)
        col = None
        if hasattr(attr, "prop") and hasattr(attr.prop, "columns") and attr.prop.columns:
            col = attr.prop.columns[0]
        elif hasattr(attr, "column"):
            col = attr.column
        
        if col is not None:
            return col.default is not None or col.server_default is not None
        return False

    print(f"stock has default: {has_default(MaturityProduct, 'stock')}")
    print(f"price has default: {has_default(MaturityProduct, 'price')}")

    p = MaturityProduct(name="Test", price=100)
    print(f"Product stock value: {p.stock}")
    print(f"Product stock in __dict__: {'stock' in p.__dict__}")
    
    try:
        await p.full_clean()
        print("Validation passed!")
    except ValidationErrors as e:
        print(f"Validation failed: {e.errors}")

    await database.disconnect()

if __name__ == "__main__":
    asyncio.run(repro())
