import asyncio
from eden.db import MockDB
from eden.tenancy.context import set_current_tenant
from eden.tenancy.models import Tenant
from tests.models.foo import Foo # A tenant-isolated model

async def main():
    # Setup Tenant
    tenant = Tenant(id="a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11", slug="test1", name="Test1")
    set_current_tenant(tenant)

    # Use a dummy session
    db = await MockDB.create()
    
    # Try bulk update mapping
    try:
        await Foo.bulk_update_mapping(
            [{"id": 1, "name": "new_name"}],
            session=db.session
        )
    except Exception as e:
        print("Expected failure because no real db. Exception:", e)

if __name__ == "__main__":
    asyncio.run(main())
