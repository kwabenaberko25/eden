import asyncio
import uuid
from typing import Optional, Any
from eden.db import Model, f
from eden.db.session import Database
from eden.config import Config
import os

# os.environ["EDEN_ENV"] = "test"
url = "postgresql+asyncpg://postgres:0123456789@localhost:5432/eden_tests"

class LifecycleTest(Model):
    __tablename__ = "lifecycle_test"
    name: str = f(max_length=100)
    hook_triggered: bool = f(default=False)
    
    async def before_save(self, session):
        self.hook_triggered = True

async def main():
    print(f"Connected to {url}")
    
    db = Database(url)
    await db.connect(create_tables=True)
    
    # We also need to create audit_logs table if we want to avoid the error 
    # but for now let's just see if LifecycleTest works.
    
    print("Creating instance...")
    try:
        async with db.session() as session:
            obj = await LifecycleTest.create(name="Test Hooks", session=session)
            print(f"Object created with ID: {obj.id}")
            print(f"Hook triggered: {obj.hook_triggered}")
            
            # Commit handled by the transaction in save()
            
            # Reload
            fetched = await LifecycleTest.get(id=obj.id, session=session)
            print(f"Fetched hook triggered: {fetched.hook_triggered if fetched else 'FETCH FAILED'}")
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
