
import sys
import os
import asyncio
from typing import List
from sqlalchemy.orm import Mapped

# Add current directory to path
sys.path.append(os.getcwd())

from eden.db import Model, Database, Reference, f, Integer

class ReproUser(Model):
    __tablename__ = "repro_users"
    id: Mapped[int] = f(primary_key=True)
    name: Mapped[str] = f()

class ReproSocialAccount(Model):
    __tablename__ = "repro_social_accounts"
    id: Mapped[int] = f(primary_key=True)
    provider: Mapped[str] = f()
    # This should link to 'repro_users', not 'users'
    user: Mapped["ReproUser"] = Reference(fk_type=Integer)

async def main():
    db = Database("sqlite+aiosqlite:///:memory:")
    print("Connecting to database...")
    try:
        await db.connect(create_tables=True)
        print("Success! Tables created.")
    except Exception as e:
        print(f"FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
