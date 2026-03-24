import asyncio
import sys
import os
import uuid
from datetime import datetime

# Add current directory to path
sys.path.append(os.getcwd())

import pytest
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String

from eden.db import Model, Database
from eden.audit import AuditableMixin
from eden.admin.models import AuditLog
from eden.db.ai import VectorModel
from eden.db.session import SessionResolutionError, set_session, reset_session

# Define a test model with auditing
class AuditedProject(AuditableMixin, Model):
    __tablename__ = "test_audited_projects"
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(String(500), nullable=True)

# Define a test model with vector search
class VectorItem(VectorModel, Model):
    __tablename__ = "test_vector_items"
    content: Mapped[str] = mapped_column(String(100))
    # We add a dummy embedding for the sake of reaching the session check
    # without crashing on getattr(cls, 'embedding')
    embedding: Mapped[str] = mapped_column(String(100), nullable=True)

async def test_auditable_mixin():
    print("Testing AuditableMixin...")
    db = Database("sqlite+aiosqlite:///:memory:")
    await db.connect(create_tables=True)
    
    # Manually bind the model to the db for testing if connect didn't do it globally
    Model._bind_db(db)
    
    async with db.transaction() as session:
        # Create a record
        project = await AuditedProject.create(name="Initial Project", description="Testing audit")
        project_id = str(project.id)
        
        # Wait a bit for the background audit task to complete
        # (Since we used asyncio.create_task in AuditableMixin)
        await asyncio.sleep(0.5)
        
        # Check if AuditLog was created
        logs = await AuditLog.query().filter(record_id=project_id, action="create").all()
        assert len(logs) >= 1, "Creation audit log missing"
        assert logs[0].changes["name"]["new"] == "Initial Project"
        print("✓ Creation audit logged")
        
        # Update the record
        project.name = "Updated Project"
        await project.save()
        await asyncio.sleep(0.5)
        
        logs = await AuditLog.query().filter(record_id=project_id, action="update").all()
        assert len(logs) >= 1, "Update audit log missing"
        assert logs[0].changes["name"]["old"] == "Initial Project"
        assert logs[0].changes["name"]["new"] == "Updated Project"
        print("✓ Update audit logged with diff")

async def test_vector_search_session_check():
    print("\nTesting Vector Search Session Check...")
    
    # Should raise SessionResolutionError if no session in context
    try:
        await VectorItem.semantic_search("test query")
        assert False, "Should have raised SessionResolutionError"
    except SessionResolutionError:
        print("✓ semantic_search correctly raises error when session is missing")

async def run_all():
    try:
        await test_auditable_mixin()
        await test_vector_search_session_check()
        print("\n✨ TIER 1 VERIFICATION SUCCESSFUL ✨")
    except Exception as e:
        print(f"\n❌ VERIFICATION FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(run_all())
