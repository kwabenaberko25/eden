
import asyncio
import os
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

from tests.test_orm_modern import ModernUser
from eden.db.validation import ValidationErrors

async def run():
    print("MRO:", [c.__name__ for c in ModernUser.mro()])
    u = ModernUser(name='T', email='e@e.com', bio='a'*505)
    print("RULES:", ModernUser._validation_rules)
    try:
        await u.full_clean()
        print("FAILED: validation didn't raise!")
    except ValidationErrors as e:
        print(f"PASSED: caught ValidationErrors: {e}")
    except Exception as e:
        print(f"FAILED: caught {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(run())
