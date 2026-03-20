
import asyncio
import uuid
from eden.app import Eden, create_app
from eden.db import Model, f, Database, set_session
from eden.config import Config, set_config

class LifecycleModel(Model):
    __tablename__ = "lifecycle_test"
    name: str = f(max_length=100)
    hook_triggered: bool = f(default=False)
    
    async def before_save(self, session):
        self.hook_triggered = True

async def main():
    config = Config()
    config.database_url = "sqlite+aiosqlite:///:memory:"
    set_config(config)
    
    app = create_app()
    db = Database(config.database_url)
    app.state.db = db
    await db.connect(create_tables=True)
    Model._bind_db(db)
    
    print("Creating instance...")
    obj = await LifecycleModel.create(name="Test Hooks")
    print(f"Object: {obj}")
    if obj:
        print(f"Hook triggered: {obj.hook_triggered}")
    else:
        print("FAILED: obj is None")

if __name__ == "__main__":
    asyncio.run(main())
