"""
Query Distinct - Remove duplicate records from query results

Allows returning only distinct/unique records based on all or specific fields:
- distinct() - Get distinct records (no duplicates)
- distinct(*fields) - Get distinct based on specific fields only
- distinct().count() - Count unique records

Usage:
    # Get distinct emails (users without duplicates)
    distinct_users = await User.objects.distinct()
    
    # Get distinct cities
    cities = await User.objects.values_list('city', flat=True).distinct()
    
    # Count unique authors
    author_count = await Post.objects.values('author_id').distinct().count()
"""

from typing import List, Set, Optional, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class DistinctQueryBuilder:
    """Builder for distinct queries."""
    
    fields: Optional[List[str]] = None  # None = all fields
    _query: str = ""
    
    def get_distinct_sql(self, table_name: str, base_query: str = "") -> str:
        """
        Generate SQL for DISTINCT query.
        
        Args:
            table_name: Name of the table
            base_query: Optional base query to extend
        
        Returns:
            SQL query with DISTINCT clause
        """
        if self.fields:
            # DISTINCT ON specific fields (PostgreSQL)
            fields_sql = ", ".join(self.fields)
            return f"SELECT DISTINCT ON ({fields_sql}) * FROM {table_name}"
        else:
            # Simple DISTINCT
            return f"SELECT DISTINCT * FROM {table_name}"
    
    def get_distinct_with_values(self, table_name: str, value_fields: List[str]) -> str:
        """Generate DISTINCT query for values/values_list."""
        fields_sql = ", ".join(value_fields)
        return f"SELECT DISTINCT {fields_sql} FROM {table_name}"


class DistinctQuerySet:
    """Mixin for QuerySet to add distinct() method."""
    
    def distinct(self, *fields: str):
        """
        Return distinct records.
        
        Args:
            *fields: Optional field names for DISTINCT ON (PostgreSQL specific)
                    If not provided, removes all duplicates
        
        Returns:
            New QuerySet with distinct flag set
        
        Usage:
            distinct_users = await User.objects.distinct()
            distinct_cities = await User.objects.distinct('city')
        """
        new_qs = self._clone() if hasattr(self, '_clone') else self
        new_qs._distinct = True
        new_qs._distinct_fields = list(fields) if fields else None
        return new_qs
    
    async def _apply_distinct(self, rows: List[Any]) -> List[Any]:
        """
        Apply distinct logic to in-memory rows.
        
        Should be called after fetching results from database.
        """
        if not hasattr(self, '_distinct') or not self._distinct:
            return rows
        
        seen = set()
        distinct_rows = []
        
        if hasattr(self, '_distinct_fields') and self._distinct_fields:
            # DISTINCT ON specific fields
            for row in rows:
                key_values = tuple(getattr(row, f, None) for f in self._distinct_fields)
                if key_values not in seen:
                    seen.add(key_values)
                    distinct_rows.append(row)
        else:
            # Simple DISTINCT - remove duplicate objects
            # For models, use id as the key
            for row in rows:
                row_id = getattr(row, 'id', id(row))
                if row_id not in seen:
                    seen.add(row_id)
                    distinct_rows.append(row)
        
        logger.debug(f"Applied distinct: {len(rows)} rows → {len(distinct_rows)} distinct")
        return distinct_rows


async def query_distinct(
    model_class: Any,
    distinct_fields: Optional[List[str]] = None,
    filter_kwargs: Optional[dict] = None
) -> List[Any]:
    """
    Query distinct records from model.
    
    Args:
        model_class: The model class to query
        distinct_fields: Optional fields to use for DISTINCT ON
        filter_kwargs: Optional WHERE conditions
    
    Returns:
        List of distinct model instances
    
    Usage:
        distinct_users = await query_distinct(User)
        distinct_active = await query_distinct(
            User,
            filter_kwargs={'is_active': True}
        )
    """
    table_name = model_class.__tablename__
    builder = DistinctQueryBuilder(fields=distinct_fields)
    
    # Build WHERE clause if provided
    where_clause = ""
    params = []
    if filter_kwargs:
        conditions = []
        for i, (key, value) in enumerate(filter_kwargs.items(), 1):
            conditions.append(f"{key} = ${i}")
            params.append(value)
        where_clause = " WHERE " + " AND ".join(conditions)
    
    # Build query
    if distinct_fields:
        fields_sql = ", ".join(distinct_fields)
        query = f"SELECT DISTINCT ON ({fields_sql}) * FROM {table_name}{where_clause}"
    else:
        query = f"SELECT DISTINCT * FROM {table_name}{where_clause}"
    
    try:
        if hasattr(model_class, 'db_connection') and model_class.db_connection:
            rows = await model_class.db_connection.fetch(query, *params)
            results = [model_class(**dict(row)) for row in rows]
            logger.info(f"Query distinct: {len(results)} unique records")
            return results
    except Exception as e:
        logger.error(f"Query distinct failed: {e}")
        raise
    
    return []


async def count_distinct(
    model_class: Any,
    field_name: str = "id",
    filter_kwargs: Optional[dict] = None
) -> int:
    """
    Count distinct values of a field.
    
    Args:
        model_class: The model class
        field_name: Field to count distinct values (default: id)
        filter_kwargs: Optional WHERE conditions
    
    Returns:
        Count of distinct values
    
    Usage:
        unique_authors = await count_distinct(Post, 'author_id')
    """
    table_name = model_class.__tablename__
    
    # Build WHERE clause
    where_clause = ""
    params = []
    if filter_kwargs:
        conditions = []
        for i, (key, value) in enumerate(filter_kwargs.items(), 1):
            conditions.append(f"{key} = ${i}")
            params.append(value)
        where_clause = " WHERE " + " AND ".join(conditions)
    
    query = f"SELECT COUNT(DISTINCT {field_name}) as count FROM {table_name}{where_clause}"
    
    try:
        if hasattr(model_class, 'db_connection') and model_class.db_connection:
            result = await model_class.db_connection.fetchval(query, *params)
            return int(result) if result else 0
    except Exception as e:
        logger.error(f"Count distinct failed: {e}")
        raise
    
    return 0
