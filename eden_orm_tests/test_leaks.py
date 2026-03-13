import asyncio
import sys
import os
from unittest.mock import MagicMock, AsyncMock

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import eden_orm
from eden_orm import Model, StringField, initialize

class MockRecord(dict):
    pass

async def run_leak_test():
    # Setup mock asyncpg
    mock_conn = AsyncMock()
    mock_conn.fetch.return_value = []
    mock_conn.fetchrow.return_value = None
    mock_conn.fetchval.return_value = 1
    
    mock_pool = AsyncMock()
    mock_pool.acquire.return_value = mock_conn
    
    # Track releases
    release_count = 0
    async def mock_release(conn, **kwargs):
        nonlocal release_count
        release_count += 1
    
    mock_pool.release = mock_release
    
    # Patch asyncpg.create_pool
    import asyncpg
    asyncpg.create_pool = AsyncMock(return_value=mock_pool)
    
    # Initialize ORM
    await initialize("postgresql://user:pass@localhost/db")
    
    print(f"Initial acquire count: {mock_pool.acquire.call_count}")
    print(f"Initial release count: {release_count}")
    
    # Define a model
    class User(Model):
        __tablename__ = "users"
        name = StringField()
        
    # Test save() leak
    print("\nTesting User.save()...")
    user = User(name="Test")
    await user.save()
    print(f"Acquire count after save: {mock_pool.acquire.call_count}")
    print(f"Release count after save: {release_count}")
    
    # Test all() leak
    print("\nTesting User.all()...")
    await User.all()
    print(f"Acquire count after all: {mock_pool.acquire.call_count}")
    print(f"Release count after all: {release_count}")
    
    # Test filter().all() leak
    print("\nTesting User.filter().all()...")
    await User.filter(name="Test").all()
    print(f"Acquire count after filter.all: {mock_pool.acquire.call_count}")
    print(f"Release count after filter.all: {release_count}")
    
    # Summary
    leaks = mock_pool.acquire.call_count - release_count
    print(f"\nFinal Summary:")
    print(f"Total Acquires: {mock_pool.acquire.call_count}")
    print(f"Total Releases: {release_count}")
    print(f"Net Leaks: {leaks}")
    
    if leaks > 0:
        print("FAIL: Connection leak detected!")
    else:
        print("PASS: No connection leak detected.")

if __name__ == "__main__":
    asyncio.run(run_leak_test())
