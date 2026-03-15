import pytest
import asyncio
from eden.db import parse_lookups
from eden.db import Model
from eden.db import StringField
from unittest.mock import AsyncMock, MagicMock

class DummyModel(Model):
    __tablename__ = "dummy_model"
    name = StringField()

@pytest.mark.asyncio
async def test_parse_lookups_like_vulnerability():
    """
    Test if parse_lookups correctly escapes LIKE wildcards to prevent DoS via %.
    """
    user_input = "100%"
    expressions = parse_lookups(DummyModel, name__icontains=user_input)
    expr = expressions[0]
    
    # Compile the expression to SQL string
    compiled = str(expr.compile(compile_kwargs={"literal_binds": True}))
    print(f"\nCompiled SQL: {compiled}")
    
    # Ideally, '%100\%%' or an ESCAPE clause should be present.
    # We'll assert that the wildcard is escaped.
    assert "ESCAPE" in compiled.upper() or r"\%" in compiled, "Vulnerable: Wildcards % and _ are not escaped in LIKE/ILIKE lookups."

@pytest.mark.asyncio
async def test_tenant_middleware_schema_leak():
    """
    Test if TenantMiddleware resets the db search_path back to public.
    """
    from eden.tenancy.middleware import TenantMiddleware
    from eden.requests import Request
    
    # Mock ASGI App
    app = MagicMock()
    app.add_middleware = MagicMock()
    
    # Init Middleware
    middleware = TenantMiddleware(app, strategy="header")
    
    import eden.tenancy.middleware
    
    scope = {
        "type": "http",
        "method": "GET",
        "headers": [(b"host", b"testserver"), (b"x-tenant-id", b"tenant_a")],
        "path": "/",
    }
    
    # We will mock the tenant object
    mock_tenant = MagicMock()
    mock_tenant.schema_name = "tenant_a_schema"
    
    # Mock _resolve_tenant
    middleware._resolve_tenant = AsyncMock(return_value=mock_tenant)
    
    class MockSession:
        async def execute(self, stmt):
            self.last_stmt = str(stmt)
            
    mock_session = MockSession()
    
    class MockDBManager:
        def __init__(self):
            self.schema_calls = []
        async def set_schema(self, session, schema_name):
            self.schema_calls.append(schema_name)

    mock_db_manager = MockDBManager()
    
    import eden.db
    eden.db.get_db = MagicMock(return_value=mock_db_manager)
    
    async def call_next(request):
        # By the time the view is called, the schema should be the tenant's schema
        assert mock_db_manager.schema_calls == ["tenant_a_schema"]
        return JSONResponse({"status": "ok"})
        
    from starlette.responses import JSONResponse
    
    # Make a dummy request
    request = Request(scope)
    request.state.db = mock_session
    request.state.tenant = mock_tenant
    
    await middleware.dispatch(request, call_next)
    
    # We expect set_schema to have been called with "tenant_a_schema" then "public"
    assert mock_db_manager.schema_calls == ["tenant_a_schema", "public"], "Tenant isolation leak: DB connection schema was not reset at the end of the request!"
