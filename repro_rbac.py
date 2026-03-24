
import asyncio
import uuid
from eden.db import Model, f, Database
from eden.db.access import AccessControl
from eden.tenancy.registry import tenancy_registry

class SimpleTask(Model):
    __tablename__ = "simple_tasks"
    title: str = f()

async def repro():
    db = Database("sqlite+aiosqlite:///:memory:")
    await db.connect()
    async with db.engine.begin() as conn:
        await conn.run_sync(Model.metadata.create_all)

    # Check RBAC
    filters = SimpleTask.get_security_filters(None, "read")
    print(f"RBAC Filters for SimpleTask (read): {filters}")
    
    # Check Tenancy
    is_isolated = tenancy_registry.is_isolated(SimpleTask)
    print(f"Is SimpleTask isolated? {is_isolated}")

    # Try CRUD
    task = await SimpleTask.create(title="Test Task")
    print(f"Created task with ID: {task.id}")
    
    fetched = await SimpleTask.get(task.id)
    print(f"Fetched task: {fetched}")
    
    if fetched is None:
        print("FAILURE: Could not fetch task after creation!")

if __name__ == "__main__":
    asyncio.run(repro())
