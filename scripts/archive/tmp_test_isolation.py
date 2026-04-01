
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import Column, Integer, String, select
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import StaticPool

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String)

async def run_test():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool, echo=True)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Simulation of test 1
    async with engine.connect() as conn1:
        print(f"Conn 1 ID: {id(conn1)}")
        trans1 = await conn1.begin()
        
        # Option A: join_transaction_mode
        session1 = AsyncSession(bind=conn1, join_transaction_mode="create_savepoint")
        await session1.begin() # Should be a savepoint
        
        session1.add(User(name="test1"))
        await session1.commit() # Should commit savepoint
        
        # Verify it exists in conn 1
        res = await conn1.execute(select(User))
        print(f"Conn 1 Users: {res.scalars().all()}")
        
        await trans1.rollback()
        print("Conn 1 Rolled back")

    # Simulation of test 2
    async with engine.connect() as conn2:
        print(f"Conn 2 ID: {id(conn2)}")
        res = await conn2.execute(select(User))
        users = res.scalars().all()
        print(f"Conn 2 Users: {users}")
        if not users:
            print("SUCCESS: Isolation worked with join_transaction_mode")
        else:
            print("FAILURE: Isolation failed with join_transaction_mode")

    # Simulation of test 1 (nested)
    async with engine.connect() as conn1:
        trans1 = await conn1.begin()
        session1 = AsyncSession(bind=conn1)
        nested = await session1.begin_nested()
        
        session1.add(User(name="test2"))
        await session1.commit() # Does this commit the nested one?
        
        await trans1.rollback()
        print("Conn 1 (nested) Rolled back")

    async with engine.connect() as conn2:
        res = await conn2.execute(select(User))
        users = res.scalars().all()
        print(f"Conn 2 (after nested) Users: {users}")
        if not users:
            print("SUCCESS: Isolation worked with explicit begin_nested")

if __name__ == "__main__":
    asyncio.run(run_test())
