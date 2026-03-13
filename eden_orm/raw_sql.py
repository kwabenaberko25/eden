"""
Eden ORM - Raw SQL Query Interface

Provides a simplified API for executing raw SQL queries while maintaining type safety.
"""

from typing import Any, List, Dict, Optional, Type, Union
import logging
import re

logger = logging.getLogger(__name__)


class RawQuery:
    """Interface for executing raw SQL queries."""
    
    @staticmethod
    async def execute(
        sql: str,
        params: Optional[List[Any]] = None,
        fetch_one: bool = False
    ) -> Union[List[Dict[str, Any]], Dict[str, Any], None]:
        """
        Execute a raw SQL query.
        
        Usage:
            results = await RawQuery.execute(
                "SELECT * FROM users WHERE email = $1",
                ["user@example.com"]
            )
            
            user = await RawQuery.execute(
                "SELECT * FROM users WHERE id = $1",
                [user_id],
                fetch_one=True
            )
        
        Args:
            sql: SQL query string with $1, $2 style parameters
            params: List of parameters to bind
            fetch_one: If True, return single dict; if False return list of dicts
        
        Returns:
            Single dict, list of dicts, or None if fetch_one=True and no results
        """
        from .connection import get_session
        
        session = await get_session()
        
        try:
            if fetch_one:
                row = await session.fetchrow(sql, *(params or []))
                if row is None:
                    return None
                return dict(row)
            else:
                rows = await session.fetch(sql, *(params or []))
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Raw SQL query failed: {e}")
            logger.error(f"SQL: {sql}")
            logger.error(f"Params: {params}")
            raise
    
    @staticmethod
    async def execute_scalar(
        sql: str,
        params: Optional[List[Any]] = None
    ) -> Any:
        """
        Execute query expecting single scalar value.
        
        Usage:
            count = await RawQuery.execute_scalar(
                "SELECT COUNT(*) as count FROM users"
            )
            
            email = await RawQuery.execute_scalar(
                "SELECT email FROM users WHERE id = $1",
                [user_id]
            )
        
        Args:
            sql: SQL query
            params: Query parameters
        
        Returns:
            Single scalar value
        """
        from .connection import get_session
        
        session = await get_session()
        
        try:
            result = await session.fetchval(sql, *(params or []))
            return result
        except Exception as e:
            logger.error(f"Raw SQL scalar query failed: {e}")
            raise
    
    @staticmethod
    async def execute_update(
        sql: str,
        params: Optional[List[Any]] = None
    ) -> int:
        """
        Execute INSERT/UPDATE/DELETE and return affected row count.
        
        Usage:
            count = await RawQuery.execute_update(
                "UPDATE users SET is_active = $1 WHERE id = $2",
                [True, user_id]
            )
            
            count = await RawQuery.execute_update(
                "DELETE FROM users WHERE created_at < $1",
                [cutoff_date]
            )
        
        Args:
            sql: SQL query
            params: Query parameters
        
        Returns:
            Number of affected rows
        """
        from .connection import get_session
        
        session = await get_session()
        
        try:
            result = await session.execute(sql, *(params or []))
            # Parse result string like "UPDATE 5" or "DELETE 3"
            if isinstance(result, str):
                parts = result.split()
                if len(parts) >= 2:
                    try:
                        return int(parts[-1])
                    except ValueError:
                        return 0
            return 0
        except Exception as e:
            logger.error(f"Raw SQL update query failed: {e}")
            raise


class ModelRawQuery:
    """Raw query methods attached to model classes."""
    
    @staticmethod
    def raw(model_class: Type):
        """
        Return a raw query interface bound to a model.
        
        Usage:
            users = await User.raw(
                "SELECT * FROM users WHERE email LIKE $1",
                ["%@example.com"]
            )
        """
        async def _raw_query(sql: str, params: Optional[List[Any]] = None):
            results = await RawQuery.execute(sql, params, fetch_one=False)
            
            # Convert dict results to model instances
            instances = []
            for row in results:
                instance = model_class()
                for field_name in model_class.__fields__:
                    if field_name in row:
                        setattr(instance, field_name, row[field_name])
                instances.append(instance)
            
            return instances
        
        return _raw_query


# Convenience functions for common patterns

async def raw_select(
    table: str,
    where: Optional[str] = None,
    params: Optional[List[Any]] = None
) -> List[Dict[str, Any]]:
    """
    Execute a SELECT query with optional WHERE.
    
    Usage:
        users = await raw_select("users", "email = $1", ["user@example.com"])
    """
    sql = f"SELECT * FROM {table}"
    if where:
        sql += f" WHERE {where}"
    
    return await RawQuery.execute(sql, params)


async def raw_count(
    table: str,
    where: Optional[str] = None,
    params: Optional[List[Any]] = None
) -> int:
    """
    Count rows in a table.
    
    Usage:
        count = await raw_count("users", "is_active = $1", [True])
    """
    sql = f"SELECT COUNT(*) as count FROM {table}"
    if where:
        sql += f" WHERE {where}"
    
    result = await RawQuery.execute_scalar(sql, params)
    return result or 0


async def raw_insert(
    table: str,
    values: Dict[str, Any]
) -> int:
    """
    Insert a row and return affected count.
    
    Usage:
        count = await raw_insert("users", {
            "email": "user@example.com",
            "name": "User"
        })
    """
    if not values:
        raise ValueError("values dict cannot be empty")
    
    columns = list(values.keys())
    placeholders = [f"${i+1}" for i in range(len(columns))]
    
    sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"
    params = list(values.values())
    
    return await RawQuery.execute_update(sql, params)


async def raw_update(
    table: str,
    values: Dict[str, Any],
    where: str,
    where_params: Optional[List[Any]] = None
) -> int:
    """
    Update rows and return affected count.
    
    Usage:
        count = await raw_update(
            "users",
            {"is_active": True},
            "created_at > $1",
            [cutoff_date]
        )
    """
    if not values:
        raise ValueError("values dict cannot be empty")
    
    where_params = where_params or []
    
    set_parts = []
    params = []
    for i, (col, val) in enumerate(values.items(), 1):
        set_parts.append(f"{col} = ${i}")
        params.append(val)
    
    # Adjust where param placeholders - replace from highest index down to avoid collisions
    # e.g., $1 -> $3, but $10 should not become $30
    where_offset = len(params)
    where_adjusted = where
    
    # Replace in descending order of index to avoid collision (e.g., $10 before $1)
    if where_params:
        # Find all parameter placeholders and replace them
        def replace_param(match):
            param_num = int(match.group(1))
            new_num = param_num + where_offset
            return f"${new_num}"
        
        where_adjusted = re.sub(r'\$(\d+)', replace_param, where)
    
    sql = f"UPDATE {table} SET {', '.join(set_parts)} WHERE {where_adjusted}"
    params.extend(where_params)
    
    return await RawQuery.execute_update(sql, params)


async def raw_delete(
    table: str,
    where: str,
    params: Optional[List[Any]] = None
) -> int:
    """
    Delete rows and return affected count.
    
    Usage:
        count = await raw_delete("users", "is_active = $1", [False])
    """
    sql = f"DELETE FROM {table} WHERE {where}"
    
    return await RawQuery.execute_update(sql, params or [])
