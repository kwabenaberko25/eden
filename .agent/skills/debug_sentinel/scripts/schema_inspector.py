import asyncio
import sys
from pathlib import Path

# Ensure Eden is in path
sys.path.append(str(Path.cwd()))

from eden.config import get_config
from eden.db import Database, Model
from sqlalchemy import inspect

async def inspect_schema():
    config = get_config()
    db = Database()
    await db.connect()
    
    engine = db.engine
    inspector = inspect(engine.sync_engine)
    
    print("--- ORM SCHEMA INSPECTION ---")
    
    # 1. Get database tables
    db_tables = inspector.get_table_names()
    print(f"Tables in Database: {', '.join(db_tables)}")
    
    # 2. Get registered models
    # This assumes models are already imported, which is a catch-22 for a script
    # For now, let's just list what's in the DB and what the current logic sees
    
    for table_name in db_tables:
        print(f"\nTable: {table_name}")
        columns = inspector.get_columns(table_name)
        for col in columns:
            print(f"  - {col['name']} ({col['type']})")
            
        pk = inspector.get_pk_constraint(table_name)
        print(f"  Primary Key: {', '.join(pk['constrained_columns'])}")
        
        fks = inspector.get_foreign_keys(table_name)
        for fk in fks:
            print(f"  Foreign Key: {', '.join(fk['constrained_columns'])} -> {fk['referred_table']}.{', '.join(fk['referred_columns'])}")

    await db.disconnect()

if __name__ == "__main__":
    asyncio.run(inspect_schema())
