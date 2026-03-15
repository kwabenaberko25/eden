import os
import sys
import asyncio
import uuid
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock
from sqlalchemy import select, text
from sqlalchemy.orm import Mapped

# Add current directory to path to import eden
sys.path.append(os.getcwd())

from eden.db import Model as EdenModel, Database, Sum, Avg, Count, Min, Max, StringField
from eden.tenancy.models import Tenant
from eden.security.csrf import CSRFMiddleware
from eden.assets import eden_scripts

async def audit_model_system():
    print("\n--- 🕵️ Auditing Model System ---")
    
    class TestUser(EdenModel):
        __tablename__ = "test_audit_users"
        name: Mapped[str]
        age: Mapped[int]
        score: Mapped[float]
        bio: Mapped[str | None] = StringField(max_length=1000, nullable=True)

    db = Database("sqlite+aiosqlite:///:memory:")
    await db.connect(create_tables=True)
    
    async with db.session() as session:
        # Create users
        u1 = await TestUser.create(session, name="Alice", age=30, score=95.5)
        u2 = await TestUser.create(session, name="Bob", age=25, score=88.0)
        u3 = await TestUser.create(session, name="Charlie", age=35, score=92.0)
        
        # Test Aggregations
        print("Testing Aggegrations...")
        results = await TestUser.query(session).aggregate(
            total_age=Sum("age"),
            avg_score=Avg("score"),
            user_count=Count("id")
        )
        print(f"Results: {results}")
        assert results["total_age"] == 90
        assert round(results["avg_score"], 2) == 91.83
        assert results["user_count"] == 3
        
        # Test Annotations
        print("Testing Annotations...")
        # Add a flag for high scorers
        qs = TestUser.query(session).annotate(is_pro=TestUser.score > 90)
        results = await session.execute(qs._stmt)
        rows = results.all()
        for row in rows:
            # row is a (TestUser, is_pro) tuple-like object
            user = row[0]
            is_pro = row[1]
            print(f"User: {user.name}, Is Pro: {is_pro}")
            if user.name == "Alice": assert is_pro is True
            if user.name == "Bob": assert is_pro is False

    print("✅ Model system audit passed!")

async def audit_tenancy_isolation():
    print("\n--- 🕵️ Auditing Tenancy Isolation ---")
    
    # Mocking PG behavior for schema switching
    db = Database("postgresql+asyncpg://user:pass@localhost/db")
    db.connect = AsyncMock() # Prevent real connection
    db._engine = MagicMock()
    
    # Initialize global db
    import eden.db.session
    eden.db.session._default_db = db
    
    # Test set_schema
    session = AsyncMock()
    await db.set_schema(session, "tenant_alpha")
    session.execute.assert_called_once()
    sql = session.execute.call_args[0][0].text
    print(f"Generated SQL: {sql}")
    assert 'SET search_path TO "tenant_alpha", public' in sql
    
    print("✅ Tenancy isolation audit passed!")

async def audit_security_csrf():
    print("\n--- 🕵️ Auditing Security CSRF ---")
    
    # Check assets helper
    scripts = eden_scripts()
    print("Verifying htmx:configRequest listener in eden_scripts()...")
    assert "htmx:configRequest" in scripts
    assert "X-CSRF-Token" in scripts
    
    # Check Middleware cookie behavior
    from starlette.responses import Response
    async def app(scope, receive, send):
        response = Response("ok")
        await response(scope, receive, send)
    
    middleware = CSRFMiddleware(app)
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [],
        "session": {"eden_csrf_token": "secret-123"}
    }
    
    async def receive(): return {"type": "http.request"}
    
    headers_captured = []
    async def send(message):
        if message["type"] == "http.response.start":
            headers_captured.extend(message["headers"])

    await middleware(scope, receive, send)
    
    headers_dict = {k.decode().lower(): v.decode() for k, v in headers_captured}
    cookie_header = headers_dict.get("set-cookie", "")
    print(f"Set-Cookie: {cookie_header}")
    assert "csrftoken=secret-123" in cookie_header
    assert "HttpOnly" not in cookie_header # Must be visible for HTMX
    
    print("✅ Security CSRF audit passed!")

if __name__ == "__main__":
    asyncio.run(audit_model_system())
    asyncio.run(audit_tenancy_isolation())
    asyncio.run(audit_security_csrf())
