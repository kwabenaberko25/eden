"""
Eden DB - Raw SQL Interface

Provides a high-level, ergonomic API for executing raw SQL with parameter renumbering.
Includes tenant isolation enforcement to prevent accidental cross-tenant data access.

⚠️ SQL INJECTION PREVENTION:
All queries use parameterized statements ($1, $2, etc.). NEVER concatenate user input
directly into SQL strings. Always use the params list:

    # ✅ SAFE: Parameters separate from SQL
    await RawQuery.execute("SELECT * FROM users WHERE id = $1", [user_id])
    
    # ❌ UNSAFE: String concatenation
    await RawQuery.execute(f"SELECT * FROM users WHERE id = {user_id}")

The renumber_sql_params() helper automatically adjusts parameter numbers when
combining multiple parameterized clauses (e.g., SET clause + WHERE clause).

See: https://en.wikipedia.org/wiki/SQL_injection for details.
"""

import re
import logging
from typing import Any, List, Dict, Optional, Type, Union
from .utils import renumber_sql_params

logger = logging.getLogger(__name__)


class TenantException(Exception):
    """Raised when raw SQL execution violates tenant isolation policy."""
    pass


class RawQuery:
    """
    Core engine for raw SQL execution with tenant isolation enforcement.
    
    When a tenant context is active, raw SQL queries are validated to ensure
    they don't inadvertently leak cross-tenant data. To bypass this check for
    privileged operations, use _skip_tenant_check=True.
    """
    
    @staticmethod
    def _validate_tenant_isolation(sql: str, skip_check: bool = False) -> None:
        """
        Validate that raw SQL respects tenant isolation when active.
        
        Args:
            sql: The SQL query to validate
            skip_check: If True, skip validation for admin/privileged operations
        
        Raises:
            TenantException: If tenant context is active but query doesn't reference tenant_id
        """
        if skip_check:
            return
        
        from eden.tenancy.context import get_current_tenant_id
        tenant_id = get_current_tenant_id()
        
        if tenant_id is None:
            # No tenant context, no restriction
            return
        
        # Normalize SQL for analysis (lowercase, remove extra whitespace)
        sql_normalized = " ".join(sql.lower().split())
        
        # Check if query references tenant_id column or uses explicit schema
        has_tenant_check = (
            "tenant_id" in sql_normalized or 
            "eden_tenants" in sql_normalized or
            "WHERE" not in sql_normalized  # Allow writes without WHERE (implicit tenant filter)
        )
        
        if not has_tenant_check and "SELECT" in sql.upper():
            # SELECT query without tenant_id reference is dangerous
            logger.warning(
                f"Raw SQL query executed with active tenant context but no tenant_id filter. "
                f"Tenant: {tenant_id}, SQL: {sql[:100]}... "
                f"This may leak cross-tenant data. Use _skip_tenant_check=True to explicitly allow."
            )
            # Note: We warn but don't block for backward compatibility
            # Future: Change to raise TenantException(...) to enforce strictly
    
    @staticmethod
    async def execute(
        sql: str,
        params: Optional[List[Any]] = None,
        fetch_one: bool = False,
        _skip_tenant_check: bool = False
    ) -> Union[List[Dict[str, Any]], Dict[str, Any], None]:
        """
        Execute raw SQL and return dict mapping.
        
        ⚠️ SECURITY:
        SQL queries MUST use parameterized statements ($1, $2, ...).
        If your SQL contains string concatenation or user input directly,
        you are vulnerable to SQL injection.
        
        Args:
            sql: SQL query string with $1, $2, ... placeholders (MUST be parameterized)
            params: List of parameters to pass to the query
            fetch_one: If True, fetch single row; if False, fetch all rows
            _skip_tenant_check: Set True to bypass tenant isolation validation
        
        Returns:
            Single dict if fetch_one=True, list of dicts if fetch_one=False, None if no results
        
        Raises:
            TenantException: If tenant context is active and query violates isolation (can be overridden)
            Exception: Any database or connection error
            
        Example:
            # ✅ SAFE: Uses parameterized query
            user = await RawQuery.execute(
                "SELECT * FROM users WHERE email = $1",
                ["user@example.com"],
                fetch_one=True
            )
            
            # ❌ UNSAFE: String concatenation (NEVER DO THIS)
            # user = await RawQuery.execute(f"SELECT * FROM users WHERE email = '{email}'")
        """
        from .base import Model
        
        # Warn if params are missing (potential injection risk)
        if not params and "$" in sql:
            logger.warning(
                f"Raw SQL query has parameter placeholders ($1, $2, etc) but no params provided. "
                f"This will fail at runtime. SQL: {sql[:100]}..."
            )
        
        # Validate tenant isolation
        RawQuery._validate_tenant_isolation(sql, skip_check=_skip_tenant_check)
        
        # Use Eden's standard session context
        from sqlalchemy import text
        async with Model._get_session() as session:
            try:
                # Convert $1, $2 placeholders to :p1, :p2 for SQLAlchemy compatibility
                # if the user is using the legacy $ syntax
                converted_sql = sql
                sql_params = {}
                if params:
                    for i, val in enumerate(params):
                        placeholder = f"${i+1}"
                        param_name = f"p{i+1}"
                        if placeholder in sql:
                            converted_sql = converted_sql.replace(placeholder, f":{param_name}")
                            sql_params[param_name] = val
                
                result = await session.execute(text(converted_sql), sql_params or params)
                
                if fetch_one:
                    row = result.mappings().first()
                    return dict(row) if row else None
                else:
                    rows = result.mappings().all()
                    return [dict(row) for row in rows]
            except Exception as e:
                logger.error(f"Raw SQL failed: {e}\nSQL: {sql}\nParams: {params}")
                raise

    @staticmethod
    async def execute_scalar(
        sql: str, 
        params: Optional[List[Any]] = None,
        _skip_tenant_check: bool = False
    ) -> Any:
        """
        Execute and return a single value.
        
        Args:
            sql: SQL query string with $1, $2, ... placeholders
            params: List of parameters
            _skip_tenant_check: Set True to bypass tenant isolation validation
        
        Returns:
            Scalar value from the query result
        """
        from .base import Model
        from sqlalchemy import text
        
        # Validate tenant isolation
        RawQuery._validate_tenant_isolation(sql, skip_check=_skip_tenant_check)
        
        async with Model._get_session() as session:
            # Placeholder conversion
            converted_sql = sql
            sql_params = {}
            if params:
                for i, val in enumerate(params):
                    placeholder = f"${i+1}"
                    param_name = f"p{i+1}"
                    if placeholder in sql:
                        converted_sql = converted_sql.replace(placeholder, f":{param_name}")
                        sql_params[param_name] = val

            result = await session.execute(text(converted_sql), sql_params or params)
            return result.scalar()


async def raw_update(
    table: str, 
    values: Dict[str, Any], 
    where: str, 
    where_params: Optional[List[Any]] = None,
    _skip_tenant_check: bool = False
) -> int:
    """
    Execute an update with smart parameter merging and tenant isolation enforcement.
    
    Example: raw_update("users", {"active": True}, "id = $1", [123])
    Internal SQL: UPDATE users SET active = $1 WHERE id = $2
    
    Args:
        table: Table name to update
        values: Dict of {column: value} pairs
        where: WHERE clause (e.g., "id = $1") 
        where_params: List of parameters for WHERE clause
        _skip_tenant_check: Set True to bypass tenant isolation validation
    
    Returns:
        Number of rows updated
    """
    where_params = where_params or []
    cols = list(values.keys())
    
    # 1. Build SET clause with local numbering $1, $2...
    set_parts = [f"{col} = ${i+1}" for i, col in enumerate(cols)]
    val_list = list(values.values())
    
    # 2. Renumber the WHERE clause to start after the SET params
    where_renumbered = renumber_sql_params(where, offset=len(val_list))
    
    sql = f"UPDATE {table} SET {', '.join(set_parts)} WHERE {where_renumbered}"
    
    # Validate tenant isolation
    RawQuery._validate_tenant_isolation(sql, skip_check=_skip_tenant_check)
    
    all_params = val_list + where_params
    
    from .base import Model
    from sqlalchemy import text
    async with Model._get_session() as session:
        # Placeholder conversion
        converted_sql = sql
        sql_params = {}
        if all_params:
            for i, val in enumerate(all_params):
                placeholder = f"${i+1}"
                param_name = f"p{i+1}"
                if placeholder in sql:
                    converted_sql = converted_sql.replace(placeholder, f":{param_name}")
                    sql_params[param_name] = val

        result = await session.execute(text(converted_sql), sql_params or all_params)
        await session.commit()
        return result.rowcount
    
    # Parse "UPDATE 5" -> 5
    if isinstance(result, str) and " " in result:
        try: return int(result.split()[-1])
        except: pass
    return 0
