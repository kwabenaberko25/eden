
import asyncio
import uuid
from eden.db import Database
from eden.admin.models import AuditLog, PasswordResetToken

async def check():
    db = Database("postgresql+asyncpg://postgres:postgres@localhost:5432/eden")
    await db.connect()
    
    print("Checking tables...")
    try:
        count = await AuditLog.count()
        print(f"AuditLog count: {count}")
    except Exception as e:
        print(f"AuditLog failed: {e}")
        
    try:
        count = await PasswordResetToken.count()
        print(f"PasswordResetToken count: {count}")
    except Exception as e:
        print(f"PasswordResetToken failed: {e}")
        
    await db.disconnect()

if __name__ == "__main__":
    asyncio.run(check())
