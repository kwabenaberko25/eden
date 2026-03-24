import asyncio
import os
import sys
from uuid import uuid4

# Add project root to path
sys.path.append(os.getcwd())

from eden import Eden
from eden.versioning import APIVersion, VersionedRouter, VersionedMiddleware
from eden.responses import JsonResponse
from eden.db import Model, f
from eden.forms import Schema, BaseForm, field, FormField
from eden.tenancy.middleware import TenantMiddleware
from eden.tenancy.models import Tenant
from sqlalchemy import Column, String, Text, select, text
from pydantic import BaseModel, ValidationError

# Mocking Request for testing middleware
class MockState:
    def __init__(self):
        self.db = None
        self.tenant = None

class MockRequest:
    def __init__(self, headers=None, path="/", app=None):
        self.headers = headers or {}
        self.url = type('URL', (), {'path': path})()
        self.state = MockState()
        self.app = app
        self._form = {}

    async def form(self):
        return self._form

# 1. Test VersionedRouter Integration
def test_versioning_integration():
    print("\n--- Testing Versioning Integration ---")
    app = Eden()
    
    v1 = APIVersion("v1", default=True)
    v2 = APIVersion("v2")
    
    app.register_api_version(v1)
    app.register_api_version(v2)
    
    router = VersionedRouter()
    
    @router.get("/test", versions=["v1"])
    async def get_test_v1(request):
        return JsonResponse({"version": "v1"})
    
    @router.get("/test", versions=["v2"])
    async def get_test_v2(request):
        return JsonResponse({"version": "v2"})
    
    # This should now work and reach the mount() code we added
    app.include_router(router)
    print("SUCCESS: VersionedRouter mounted into Eden app")
    
    # Check if versions were registered
    if len(app._api_versions) == 2:
        print("SUCCESS: 2 API versions registered")
    else:
        print(f"FAIL: Expected 2 versions, got {len(app._api_versions)}")
        
    # Check if versioning middleware is injected during build
    middleware_list = app._build_middleware()
    has_versioning_mw = any(m.cls.__name__ == 'VersionedMiddleware' for m in middleware_list)
    
    if has_versioning_mw:
        print("SUCCESS: VersionedMiddleware correctly injected into stack")
    else:
        print("FAIL: VersionedMiddleware missing from stack")

# 2. Test TenantMiddleware Fix (Session Leak & RLS)
async def test_tenant_middleware():
    print("\n--- Testing TenantMiddleware (Leak Fix & RLS) ---")
    
    class MockDB:
        def __init__(self):
            self.entered = False
            self.exited = False
        
        def session(self):
            return self

        async def __aenter__(self):
            self.entered = True
            return self
            
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            self.exited = True
            
        async def execute(self, stmt, params=None):
            print(f"   DB Execute: {stmt}")
            return None

    app = Eden()
    app.state.db = MockDB()
    
    mw = TenantMiddleware(app, strategy="header", header_name="X-Tenant-ID")
    
    # Mock a resolved tenant
    tenant = Tenant(id=uuid4(), slug="acme", is_active=True)
    
    # We need to mock _fetch_tenant to skip real DB lookup
    async def mock_fetch(identifier, request):
        return tenant
    mw._fetch_tenant = mock_fetch
    
    request = MockRequest(headers={"X-Tenant-ID": "acme"}, app=app)
    
    async def call_next(req):
        print(f"   Dispatching request... Tenant in state: {getattr(req.state, 'tenant', None)}")
        return JsonResponse({"status": "ok"})
        
    await mw.dispatch(request, call_next)
    
    db = app.state.db
    if db.entered and db.exited:
        print("SUCCESS: Database session correctly entered and EXITED (Leak fixed)")
    else:
        print(f"FAIL: Session Enter/Exit state: {db.entered}/{db.exited}")

# 3. Test Nested Form Validation
def test_form_validation():
    print("\n--- Testing Nested Form Validation ---")
    
    class AddressSchema(Schema):
        city: str = field(min_length=3)
        
    class UserSchema(Schema):
        name: str
        address: AddressSchema
        
    # Test case: invalid city (too short)
    data = {"name": "John", "address": {"city": "NY"}}
    form = UserSchema.as_form(data)
    
    is_valid = form.is_valid()
    print(f"Is Valid (Expected False): {is_valid}")
    print(f"Errors: {form.errors}")
    
    if "address.city" in form.errors:
        print("SUCCESS: Nested error location 'address.city' correctly identified")
    else:
        print("FAIL: Nested error location missing")
        
    if "address" in form.errors:
        print(f"SUCCESS: Root field 'address' also has error summary: {form.errors['address']}")

# 4. Test Search Query Implementation
async def test_search_logic():
    print("\n--- Testing Search ranked SQL Generation ---")
    from sqlalchemy import create_mock_engine
    
    def dump(sql, *multiparams, **params):
        print(f"SQL: {sql.compile(dialect=engine.dialect)}")

    engine = create_mock_engine("postgresql://", dump)
    
    class Article(Model):
        __tablename__ = "articles"
        id = Column(String, primary_key=True)
        title = Column(String(255))
        content = Column(Text)
        
    from eden.db.query import QuerySet
    qs = QuerySet(Article)
    
    # We want to see 'websearch_to_tsquery' in the SQL
    try:
        search_qs = qs.search_ranked("eden web framework -legacy")
        stmt = search_qs._stmt
        # Compile statement to string
        from sqlalchemy.dialects import postgresql
        compiled_sql = str(stmt.compile(dialect=postgresql.dialect()))
        
        if "websearch_to_tsquery" in compiled_sql:
            print("SUCCESS: search_ranked uses websearch_to_tsquery")
        else:
            print("FAIL: websearch_to_tsquery not found in SQL")
            print(f"SQL was: {compiled_sql}")
            
    except Exception as e:
        print(f"FAIL: SQL generation failed: {e}")

if __name__ == "__main__":
    test_versioning_integration()
    asyncio.run(test_tenant_middleware())
    test_form_validation()
    asyncio.run(test_search_logic())
