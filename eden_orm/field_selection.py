"""
Field Selection - Control which fields are selected in queries

Allows selecting specific fields for performance optimization:
- only(*fields) - Select only these fields
- defer(*fields) - Select all fields except these
- values_list(*fields, flat=False) - Return tuples instead of model instances
- values(**fields) - Return dictionaries

Usage:
    # Only load name and email
    user = await User.objects.only('name', 'email').first()
    
    # Load all except password
    user = await User.objects.defer('password').first()
    
    # Get tuples of (name, email)
    names = await User.objects.values_list('name', 'email')
    
    # Get dictionaries
    data = await User.objects.values(name=True, email=True)
"""

from typing import List, Dict, Any, Tuple, Optional, Set
from dataclasses import dataclass, field as dc_field
import logging

logger = logging.getLogger(__name__)


@dataclass
class FieldSelector:
    """Manages which fields to select in a query."""
    
    all_fields: Set[str]
    only_fields: Optional[Set[str]] = None
    defer_fields: Optional[Set[str]] = None
    
    def __post_init__(self):
        """Validate field selection options."""
        if self.only_fields and self.defer_fields:
            raise ValueError("Cannot use both only() and defer() on same query")
    
    def get_selected_fields(self) -> List[str]:
        """Get the list of fields that should be selected."""
        if self.only_fields:
            # Intersect with available fields to be safe
            return list(self.only_fields & self.all_fields)
        elif self.defer_fields:
            # All fields except deferred ones
            return list(self.all_fields - self.defer_fields)
        else:
            # Return all fields
            return list(self.all_fields)
    
    def get_sql_select_clause(self, table_name: str) -> str:
        """Generate SQL SELECT clause for chosen fields."""
        selected = self.get_selected_fields()
        
        if not selected:
            raise ValueError("No fields selected for query")
        
        # Build: SELECT field1, field2, ... FROM table_name
        fields_sql = ", ".join([f"{table_name}.{field}" for field in selected])
        return f"SELECT {fields_sql}"


@dataclass
class ValuesQuery:
    """Represents a values() or values_list() query result."""
    
    data: List[Any]
    fields: List[str]
    is_flat: bool = False
    is_dict: bool = False
    
    def format_results(self):
        """Format results based on query type."""
        if self.is_flat and len(self.fields) == 1:
            # Return list of scalars: [1, 2, 3]
            return [row[0] if isinstance(row, tuple) else row[self.fields[0]] for row in self.data]
        elif self.is_dict:
            # Return list of dicts: [{'name': 'John', 'email': 'john@test.com'}, ...]
            return self.data
        else:
            # Return list of tuples: [('John', 'john@test.com'), ...]
            return self.data


class QuerySetFieldSelection:
    """Mixin for QuerySet to add field selection methods."""
    
    def only(self, *fields: str):
        """Select only these fields."""
        # Clone the queryset and set only_fields
        new_qs = self._clone()
        new_qs._selector = FieldSelector(
            all_fields=self._selector.all_fields if hasattr(self, '_selector') else set(),
            only_fields=set(fields)
        )
        return new_qs
    
    def defer(self, *fields: str):
        """Select all fields except these."""
        new_qs = self._clone()
        new_qs._selector = FieldSelector(
            all_fields=self._selector.all_fields if hasattr(self, '_selector') else set(),
            defer_fields=set(fields)
        )
        return new_qs
    
    async def values_list(self, *fields: str, flat: bool = False) -> List[Any]:
        """
        Return query results as list of tuples (or scalars if flat=True).
        Respects existing filter() and order_by() calls.
        
        Args:
            *fields: Field names to include
            flat: If True and only 1 field, return list of scalars instead of tuples
        
        Returns:
            List of tuples: [('John', 'john@test.com'), ...]
            Or list of scalars if flat=True: ['John', 'Jane', ...]
        """
        if not fields:
            raise ValueError("values_list() requires at least one field")
        
        selected_fields = set(fields) & self._selector.all_fields if hasattr(self, '_selector') else set(fields)
        
        if not selected_fields:
            logger.warning(f"No matching fields found in {fields}")
            return []
        
        # Build SQL query respecting existing filters and order
        fields_list = list(selected_fields)
        table_name = self.model_class.__tablename__
        select_clause = ", ".join([f"{table_name}.{f}" for f in fields_list])
        
        # Use FilterChain to build the full query with WHERE and ORDER BY
        if hasattr(self, 'filter_chain') and self.filter_chain:
            # Build query using filter_chain which includes WHERE and ORDER BY
            query = f"SELECT {select_clause} FROM {table_name}"
            
            # Add WHERE clause if filters exist
            where_clause = self.filter_chain._build_where_clause()
            if where_clause:
                query += f" WHERE {where_clause}"
            
            # Add ORDER BY if exists
            if hasattr(self, '_order_by') and self._order_by:
                order_parts = ", ".join(self._order_by)
                query += f" ORDER BY {order_parts}"
        else:
            query = f"SELECT {select_clause} FROM {table_name}"
        
        try:
            if self.db_connection:
                rows = await self.db_connection.fetch(query)
                # Convert to tuples/scalars based on flat parameter
                results = ValuesQuery(
                    data=rows,
                    fields=fields_list,
                    is_flat=flat,
                    is_dict=False
                )
                return results.format_results()
        except Exception as e:
            logger.error(f"Error in values_list query: {e}")
            return []
        
        return []
    
    async def values(self, **field_kwargs) -> List[Dict[str, Any]]:
        """
        Return query results as list of dictionaries.
        Respects existing filter() and order_by() calls.
        
        Usage:
            users = await User.objects.values(name=True, email=True)
            # Returns: [{'name': 'John', 'email': 'john@test.com'}, ...]
        
        Args:
            **field_kwargs: Field names to include (value should be True)
        
        Returns:
            List of dictionaries
        """
        fields = [k for k, v in field_kwargs.items() if v]
        
        if not fields:
            raise ValueError("values() requires at least one field with value=True")
        
        # Build SQL query respecting existing filters and order
        table_name = self.model_class.__tablename__
        select_clause = ", ".join([f"{table_name}.{f}" for f in fields])
        
        # Use FilterChain to build the full query with WHERE and ORDER BY
        if hasattr(self, 'filter_chain') and self.filter_chain:
            query = f"SELECT {select_clause} FROM {table_name}"
            
            # Add WHERE clause if filters exist
            where_clause = self.filter_chain._build_where_clause()
            if where_clause:
                query += f" WHERE {where_clause}"
            
            # Add ORDER BY if exists
            if hasattr(self, '_order_by') and self._order_by:
                order_parts = ", ".join(self._order_by)
                query += f" ORDER BY {order_parts}"
        else:
            query = f"SELECT {select_clause} FROM {table_name}"
        
        try:
            if self.db_connection:
                rows = await self.db_connection.fetch(query)
                # Convert rows to dicts
                result_dicts = []
                for row in rows:
                    row_dict = dict(zip(fields, [row[f] for f in fields]))
                    result_dicts.append(row_dict)
                return result_dicts
        except Exception as e:
            logger.error(f"Error in values query: {e}")
            return []
        
        return []


def optimize_select_query(model_class, field_names: List[str]) -> str:
    """
    Build optimized SELECT query with only specified fields.
    
    Args:
        model_class: The model class
        field_names: List of field names to select
    
    Returns:
        SQL query string with only selected fields
    """
    if not field_names:
        field_names = [f.name for f in model_class._fields]
    
    table_name = model_class.__tablename__
    fields_sql = ", ".join([f"{table_name}.{name}" for name in field_names])
    
    return f"SELECT {fields_sql} FROM {table_name}"
