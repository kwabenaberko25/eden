import asyncio
import logging
import uuid
import os
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.pool import NullPool
from sqlalchemy import text

# Standard Eden imports
from eden.db import Model, Database
from eden.db.migrations import MigrationManager
from eden.tenancy.models import Tenant
from eden.config import ConfigManager
from eden.db.discovery import discover_models

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verify_migrations")

async def verify():
    # Ensure EDEN_ENV is test
    os.environ["EDEN_ENV"] = "test"
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("DATABASE_URL not set")
        return

    print(f"Verifying tenant migrations on {url}")
    ConfigManager.instance().reset() # Ensure fresh config
    
    # 1. CLEANUP
    engine = create_async_engine(url, poolclass=NullPool)
    async with engine.connect() as conn:
        print("Cleaning up old schemas...")
        try:
            await conn.execute(text("""
                SELECT pg_terminate_backend(pid) 
                FROM pg_stat_activity 
                WHERE datname = current_database() AND pid <> pg_backend_pid();
            """))
            await conn.commit()
        except: pass

        for schema in ['tenant_x', 'tenant_y']:
            await conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        
        await conn.execute(text('DROP SCHEMA IF EXISTS public CASCADE'))
        await conn.execute(text('CREATE SCHEMA public'))
        await conn.execute(text('GRANT ALL ON SCHEMA public TO public'))
        await conn.execute(text('GRANT ALL ON SCHEMA public TO CURRENT_USER'))
        
        for schema in ['tenant_x', 'tenant_y']:
            await conn.execute(text(f'CREATE SCHEMA "{schema}"'))
            await conn.execute(text(f'GRANT ALL ON SCHEMA "{schema}" TO public'))
            await conn.execute(text(f'GRANT ALL ON SCHEMA "{schema}" TO CURRENT_USER'))
            
        await conn.commit()
    await engine.dispose()

    discover_models()

    # 2. Migrate Public
    print("Migrating public schema to head...")
    manager_pub = MigrationManager(url)
    await manager_pub.migrate(revision="head")

    await asyncio.sleep(1)

    # 3. SEED TENANTS
    print("Seeding tenants...")
    db = Database(url)
    await db.connect()
    
    async with db.session() as session:
        # Inspect tables
        all_tables = await session.execute(text("""
            SELECT schemaname, tablename 
            FROM pg_tables 
            WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
        """))
        found_tables = all_tables.fetchall()
        print(f"  - All tables in DB: {[(t[0], t[1]) for t in found_tables]}")

        try:
            tx = await Tenant.create(session=session, name="Tenant X", slug="tenant_x_slug", schema_name="tenant_x")
            ty = await Tenant.create(session=session, name="Tenant Y", slug="tenant_y_slug", schema_name="tenant_y")
            await session.commit()
            print(f"Created tenants in public: {tx.id}, {ty.id}")
        except Exception as e:
            print(f"ERROR creating tenants: {e}")
            await db.disconnect()
            return

    # 4. SETUP TENANT SCHEMAS
    print("Setting up tenants at old revision (d2d3b0a786fd)...")
    for schema in ['tenant_x', 'tenant_y']:
        print(f"  - Provisioning {schema}...")
        # We manually stamp instead of migrate all the way, to simulate needing an upgrade
        # STAMP to initial
        await manager_pub.migrate(revision="d2d3b0a786fd", schema=schema)
        # Actually, let's just stamp it.
        # await manager_pub.stamp(revision="d2d3b0a786fd", schema=schema)
    
    # 5. RUN BATCH MIGRATION
    print("Running batch migration for all tenants to 'head'...")
    await manager_pub.migrate_tenants(revision="head")

    # 6. VERIFY
    print("Checking final versions...")
    async with db.session() as session:
        for schema in ['tenant_x', 'tenant_y']:
            res = await session.execute(text(f'SELECT version_num FROM "{schema}".alembic_version_tenant'))
            version = res.scalar()
            print(f"  - {schema} version: {version}")

    await db.disconnect()
    print("Verification complete")

if __name__ == "__main__":
    asyncio.run(verify())
