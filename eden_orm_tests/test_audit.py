import asyncio
import sys
import os
from unittest.mock import MagicMock, AsyncMock

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import eden_orm
from eden_orm import Model, StringField, ForeignKeyField, initialize, add_queryset_methods
from eden_orm.query import QuerySet

async def run_audit_tests():
    # Setup mock asyncpg
    mock_conn = AsyncMock()
    mock_conn.fetch.return_value = []
    mock_conn.fetchrow.return_value = None
    mock_conn.fetchval.return_value = 1
    
    mock_pool = AsyncMock()
    mock_pool.acquire.return_value = mock_conn
    
    release_count = 0
    async def mock_release(conn, **kwargs):
        nonlocal release_count
        release_count += 1
    mock_pool.release = mock_release
    
    import asyncpg
    asyncpg.create_pool = AsyncMock(return_value=mock_pool)
    
    await initialize("postgresql://user:pass@localhost/db")

    # Define Models
    class Author(Model):
        __tablename__ = "authors"
        name = StringField()

    class Post(Model):
        __tablename__ = "posts"
        title = StringField()
        author_id = ForeignKeyField("authors")

    # Manually register methods since the ORM doesn't do it
    add_queryset_methods(Author)
    add_queryset_methods(Post)

    print("--- 1. Connection Leak Test ---")
    user = Author(name="Author 1")
    await user.save()
    await Author.all()
    await Author.filter(name="Author 1").all()
    
    leaks = mock_pool.acquire.call_count - release_count
    print(f"Total Acquires: {mock_pool.acquire.call_count}")
    print(f"Total Releases: {release_count}")
    print(f"Net Leaks: {leaks}")
    if leaks > 0:
        print("RESULT: FAIL (Connection leak detected)")
    else:
        print("RESULT: PASS")

    print("\n--- 2. Select Related Column Bug Test ---")
    # Reset mock to capture SQL
    mock_conn.fetch.reset_mock()
    
    # We need to set Author on Post's FK field manually for select_related to work
    Post.__fields__['author_id'].to_model = Author
    
    await Post.filter(title="Test").select_related("author").all()
    
    last_query = mock_conn.fetch.call_args[0][0]
    print(f"Generated SQL: {last_query}")
    
    if "authors.*" not in last_query and "authors.name" not in last_query:
        print("RESULT: FAIL (select_related is missing columns from the joined table!)")
    else:
        print("RESULT: PASS")

    print("\n--- 3. Bulk Create Parameter Bug Test ---")
    from eden_orm.bulk import BulkOperations
    posts = [Post(title="P1"), Post(title="P2")]
    
    try:
        await BulkOperations.bulk_create(Post, posts)
    except Exception as e:
        print(f"Bulk create failed as expected or with error: {e}")
    
    last_bulk_query = mock_conn.fetch.call_args[0][0]
    print(f"Bulk SQL: {last_bulk_query}")
    
    # Check if parameters are incrementing or repeating
    # Bad: ($1, $2), ($1, $2)
    # Good: ($1, $2), ($3, $4)
    if "($1, $2)" in last_bulk_query and last_bulk_query.count("($1, $2)") > 1:
         print("RESULT: FAIL (Bulk create repeats parameter indices!)")
    else:
         print("RESULT: PASS")

if __name__ == "__main__":
    asyncio.run(run_audit_tests())
