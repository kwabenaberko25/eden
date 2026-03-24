import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from eden import Eden
from eden.versioning import APIVersion, VersionedRouter
from eden.responses import JsonResponse
from eden.db.search import SearchQueryBuilder
from eden.db import Model, f
from sqlalchemy import Column, String, Text

# 1. Test VersionedRouter Integration
def test_versioned_router():
    print("\n--- Testing VersionedRouter Integration ---")
    app = Eden()
    
    v1 = APIVersion("v1", default=True)
    v2 = APIVersion("v2")
    
    # Check if register_api_version exists (Audit said it might be missing)
    if not hasattr(app, "register_api_version"):
        print("FAIL: Eden instance has no register_api_version method")
    
    router = VersionedRouter()
    
    @router.get("/test", versions=["v1"])
    async def get_test_v1(request):
        return JsonResponse({"version": "v1"})
    
    @router.get("/test", versions=["v2"])
    async def get_test_v2(request):
        return JsonResponse({"version": "v2"})
    
    try:
        app.include_router(router)
        print("SUCCESS: app.include_router(router) accepted VersionedRouter")
    except Exception as e:
        print(f"FAIL: app.include_router(router) failed: {e}")

# 2. Test SearchQueryBuilder with search_ranked
async def test_search_logic():
    print("\n--- Testing SearchQueryBuilder Logic ---")
    
    class Article(Model):
        title = Column(String(255))
        content = Column(Text)
    
    builder = SearchQueryBuilder()
    builder.add_term("eden")
    builder.add_phrase("web framework")
    builder.exclude("legacy")
    query_str = builder.build()
    
    print(f"Built Query: {query_str}")
    
    # Mocking QuerySet.search_ranked check
    # We want to see if it uses plainly or websearch
    from eden.db.query import QuerySet
    qs = Article.query()
    
    # We can't easily run the SQL without a real DB, but we can inspect the generated SQL
    # if we mock the engine.
    try:
        # search_ranked expects a query string
        search_qs = qs.search_ranked(query_str)
        # Note: We need a real session to compile properly with literal_binds in some cases,
        # but let's see if we can get the statement.
        print("SUCCESS: search_ranked() called successfully")
    except Exception as e:
        print(f"FAIL: search_ranked() failed: {e}")

if __name__ == "__main__":
    test_versioned_router()
    asyncio.run(test_search_logic())
