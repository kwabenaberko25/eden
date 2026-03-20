
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def check_db():
    url = "postgresql+asyncpg://postgres:0123456789@localhost:5432/postgres"
    print(f"Connecting to {url}...")
    engine = create_async_engine(url)
    try:
        async with engine.connect() as conn:
            print("Connected to PostgreSQL successfully.")
            # Check if eden_tests exists
            result = await conn.execute(text("SELECT 1 FROM pg_database WHERE datname='eden_tests'"))
            exists = result.scalar()
            if not exists:
                # Need to use a non-transactional connection to create database
                # But for simplicity, we'll try to execute it. 
                # Note: CREATE DATABASE CANNOT be run in a transaction block.
                # SQLAlchemy usually handles this if we set isolation_level to AUTOCOMMIT.
                pass

        if not exists:
            # Create a new engine with AUTOCOMMIT to create the database
            autocommit_engine = create_async_engine(url, isolation_level="AUTOCOMMIT")
            async with autocommit_engine.connect() as conn:
                await conn.execute(text("CREATE DATABASE eden_tests"))
                print("Created 'eden_tests' database.")
            await autocommit_engine.dispose()
        else:
            print("'eden_tests' database already exists.")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check_db())
