"""
Mock asyncpg module for testing without PostgreSQL

This allows tests to run without requiring actual PostgreSQL connection.
"""

class Record(dict):
    """Mock asyncpg.Record as dict-like"""
    def __getitem__(self, key):
        return super().__getitem__(key)


class Connection:
    """Mock PostgreSQL connection"""
    async def fetch(self, sql, *args):
        return []
    
    async def fetchrow(self, sql, *args):
        return None
    
    async def execute(self, sql, *args):
        return None


class Pool:
    """Mock connection pool"""
    async def acquire(self):
        return Connection()
    
    async def release(self, conn):
        pass


async def create_pool(dsn, **kwargs):
    """Create mock pool"""
    return Pool()
