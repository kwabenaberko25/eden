import asyncio
import os
import sys
import argparse
from pathlib import Path

# --- TEMPLATE ---
REPRO_TEMPLATE = """
import asyncio
import os
import sys
from pathlib import Path

# Ensure Eden is in path
sys.path.append(str(Path.cwd()))

from eden.config import create_config, set_config
from eden.db import (
    Database, Model, StringField, IntField, FloatField, BoolField,
    ForeignKeyField, Relationship, Reference, ManyToManyField
)

async def run_reproduction():
    # 1. Setup Test Environment
    config = create_config(
        env="test",
        database_url="sqlite+aiosqlite:///:memory:",
        debug=True
    )
    set_config(config)
    
    # 2. Define Models
    {models_definition}
    
    db = Database(config.database_url)
    await db.connect(create_tables=True)
    
    # 4. Run Failing Logic
    print("--- STARTING REPRODUCTION ---")
    try:
        {failing_logic}
        print("--- REPRODUCTION FINISHED SUCCESSFULLY ---")
    except Exception as e:
        print(f"--- REPRODUCTION FAILED ---")
        import traceback
        traceback.print_exc()
    finally:
        await db.disconnect()

if __name__ == "__main__":
    asyncio.run(run_reproduction())
"""

def generate_repro(name, models_code, logic_code):
    Path("tmp").mkdir(exist_ok=True)
    filename = f"tmp/repro_{name}.py"
    
    content = REPRO_TEMPLATE.format(
        models_definition=models_code,
        failing_logic=logic_code
    )
    
    with open(filename, "w") as f:
        f.write(content)
    
    return filename

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a standalone Eden reproduction script.")
    parser.add_argument("--name", required=True, help="Name of the reproduction (e.g. orm_bug)")
    parser.add_argument("--models", help="Python code defining models, or path to a file containing them")
    parser.add_argument("--logic", help="Python code for the failing logic, or path to a file containing it")
    
    args = parser.parse_args()
    
    models_content = args.models or "# No models defined"
    if os.path.exists(models_content):
        with open(models_content, "r") as f:
            models_content = f.read()
            
    logic_content = args.logic or "pass"
    if os.path.exists(logic_content):
        with open(logic_content, "r") as f:
            logic_content = f.read()
            
    # Indent logic content to match the template
    logic_content = "\n        ".join(logic_content.strip().split("\n"))
    
    filepath = generate_repro(args.name, models_content, logic_content)
    print(f"Reproduction script generated at: {filepath}")
