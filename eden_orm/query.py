"""
Eden ORM - QuerySet

Lazy-evaluated query builder for filtering, sorting, and pagination.
"""

from typing import Any, List, Optional, Dict, Type, Union
from dataclasses import dataclass, field as dc_field
import logging

from .connection import get_session
from .executor import QueryExecutor, SQLBuilder, ResultMapper
from .fields import Field

logger = logging.getLogger(__name__)


@dataclass
class Query:
    """Represents a single WHERE clause condition."""
    
    field: str
    operator: str  # exact, icontains, gte, lte, in, startswith, etc.
    value: Any


@dataclass
class FilterChain:
    """
    Represents a chain of filters to apply.
    
    Implements lazy evaluation - doesn't execute until .all(), .first(), etc.
    """
    
    model_class: Type
    conditions: List[Query] = dc_field(default_factory=list)
    order_fields: List[str] = dc_field(default_factory=list)
    limit_value: Optional[int] = None
    offset_value: Optional[int] = None
    select_related_fields: List[str] = dc_field(default_factory=list)
    prefetch_related_fields: List[str] = dc_field(default_factory=list)
    
    def filter(self, **kwargs) -> "FilterChain":
        """
        Add AND condition(s).
        
        Supports both explicit field names and double-underscore lookup syntax:
        - User.filter(email='test@example.com')  # exact match
        - User.filter(email__icontains='test')    # contains
        - User.filter(age__gte=18)                # greater than or equal
        - User.filter(name__startswith='A')       # starts with
        - User.filter(id__in=[1, 2, 3])          # IN clause
        
        Supported operators: exact, icontains, contains, startswith, endswith,
                           gte, lte, gt, lt, in, isnull
        """
        for key, value in kwargs.items():
            field_name, operator = self._parse_lookup(key)
            
            # Validate IN operator value
            if operator == "in" and not isinstance(value, (list, tuple)):
                raise ValueError(f"Expected list/tuple for IN operator, got {type(value)}")
            
            self.conditions.append(Query(field=field_name, operator=operator, value=value))
        return self
    
    def _parse_lookup(self, key: str) -> tuple[str, str]:
        """
        Parse a lookup key with double-underscore syntax.
        
        Example: 'email__icontains' -> ('email', 'icontains')
        
        Returns:
            (field_name, operator) tuple
        """
        if "__" not in key:
            # No operator specified, use exact match
            return key, "exact"
        
        parts = key.split("__")
        field_name = parts[0]
        operator = "__".join(parts[1:])  # Support nested lookups like parent__author__id__gt
        
        # Map shorthand operators to full names
        # (most are already full names, but support common aliases)
        operator_map = {
            "exact": "exact",
            "eq": "exact",  # Alias
            "icontains": "icontains",
            "contains": "contains",
            "startswith": "startswith",
            "endswith": "endswith",
            "gte": "gte",
            "lte": "lte",
            "gt": "gt",
            "lt": "lt",
            "in": "in",
            "isnull": "isnull",
        }
        
        if operator not in operator_map:
            raise ValueError(
                f"Unknown lookup operator: {operator}. "
                f"Supported: {', '.join(operator_map.keys())}"
            )
        
        return field_name, operator_map[operator]
    
    def filter_icontains(self, **kwargs) -> "FilterChain":
        """Add case-insensitive contains condition(s)."""
        for key, value in kwargs.items():
            self.conditions.append(Query(field=key, operator="icontains", value=value))
        return self
    
    def filter_startswith(self, **kwargs) -> "FilterChain":
        """Add startswith condition(s)."""
        for key, value in kwargs.items():
            self.conditions.append(Query(field=key, operator="startswith", value=value))
        return self
    
    def filter_endswith(self, **kwargs) -> "FilterChain":
        """Add endswith condition(s)."""
        for key, value in kwargs.items():
            self.conditions.append(Query(field=key, operator="endswith", value=value))
        return self
    
    def filter_gte(self, **kwargs) -> "FilterChain":
        """Add greater-than-or-equal condition(s)."""
        for key, value in kwargs.items():
            self.conditions.append(Query(field=key, operator="gte", value=value))
        return self
    
    def filter_lte(self, **kwargs) -> "FilterChain":
        """Add less-than-or-equal condition(s)."""
        for key, value in kwargs.items():
            self.conditions.append(Query(field=key, operator="lte", value=value))
        return self
    
    def filter_gt(self, **kwargs) -> "FilterChain":
        """Add greater-than condition(s)."""
        for key, value in kwargs.items():
            self.conditions.append(Query(field=key, operator="gt", value=value))
        return self
    
    def filter_lt(self, **kwargs) -> "FilterChain":
        """Add less-than condition(s)."""
        for key, value in kwargs.items():
            self.conditions.append(Query(field=key, operator="lt", value=value))
        return self
    
    def filter_in(self, **kwargs) -> "FilterChain":
        """Add IN condition(s)."""
        for key, value in kwargs.items():
            if not isinstance(value, (list, tuple)):
                raise ValueError(f"Expected list/tuple for IN operator, got {type(value)}")
            self.conditions.append(Query(field=key, operator="in", value=value))
        return self
    
    def filter_isnull(self, **kwargs) -> "FilterChain":
        """Add IS NULL / IS NOT NULL condition(s)."""
        for key, is_null in kwargs.items():
            self.conditions.append(Query(field=key, operator="isnull", value=is_null))
        return self
    
    def exclude(self, **kwargs) -> "FilterChain":
        """Add NOT condition(s)."""
        for key, value in kwargs.items():
            self.conditions.append(Query(field=key, operator="not_exact", value=value))
        return self
    
    def order_by(self, *fields: str) -> "FilterChain":
        """Add ordering."""
        self.order_fields.extend(fields)
        return self
    
    def limit(self, n: int) -> "FilterChain":
        """Add LIMIT clause."""
        self.limit_value = n
        return self
    
    def offset(self, n: int) -> "FilterChain":
        """Add OFFSET clause."""
        self.offset_value = n
        return self
    
    def select_related(self, *fields: str) -> "FilterChain":
        """
        Add eager loading via JOIN.
        
        Usage:
            posts = await Post.select_related("author").all()
            # Joins author table, avoiding N+1 queries
        """
        self.select_related_fields.extend(fields)
        return self
    
    def prefetch_related(self, *fields: str) -> "FilterChain":
        """
        Add eager loading via batch queries (separate FROM/WHERE).
        
        Alternative to select_related for when JOINs are expensive.
        Executes separate batch queries for each relationship.
        
        Usage:
            posts = await Post.prefetch_related("author", "comments").all()
            # Executes: SELECT posts, then SELECT authors WHERE id IN (...), 
            # then SELECT comments WHERE id IN (...)
        """
        self.prefetch_related_fields.extend(fields)
        return self
    
    def prefetch_nested(self, *paths: str) -> "FilterChain":
        """
        Add nested prefetch relationships with dot notation.
        
        Supports recursive prefetch with nested relationships.
        
        Usage:
            posts = await Post.filter(is_published=True).prefetch_nested(
                "author",
                "comments__author"
            ).all()
        
        Args:
            paths: Relationship paths with __ notation for nesting
        """
        # Store nested prefetch info in a special attribute
        if not hasattr(self, 'nested_prefetch_fields'):
            self.nested_prefetch_fields = []
        self.nested_prefetch_fields.extend(paths)
        return self
    
    def _build_sql(self) -> tuple[str, List[Any], Dict[str, tuple[str, str]]]:
        """Build SQL query from filter chain.
        
        Returns:
            tuple: (sql_string, params_list, alias_map)
            - alias_map: dict mapping "table_column" -> ("table", "column") for deserializing joined data
        """
        params: List[Any] = []
        base_table = self.model_class.__tablename__
        sql_parts: List[str] = []
        alias_map: Dict[str, tuple[str, str]] = {}
        
        # SELECT clause - may include joined tables
        if self.select_related_fields:
            # Select from base table - no aliases needed for base
            select_fields = [f"{base_table}.id"]
            
            # Add other base table columns
            for field_name in self.model_class.__fields__:
                if field_name != 'id':
                    select_fields.append(f"{base_table}.{field_name}")
            
            # Process select_related fields with column aliasing
            join_clauses = []
            for rel_name in self.select_related_fields:
                fk_field_name = f"{rel_name}_id"
                if fk_field_name in self.model_class.__fields__:
                    fk_field = self.model_class.__fields__[fk_field_name]
                    
                    # Get target model
                    if hasattr(fk_field, 'to_model') and fk_field.to_model:
                        target_table = fk_field.to_model.__tablename__
                        target_model = fk_field.to_model
                        
                        # Add aliased columns for target table
                        for target_field_name in target_model.__fields__:
                            # Create alias: table_field
                            alias = f"{target_table}_{target_field_name}"
                            select_fields.append(
                                f"{target_table}.{target_field_name} AS {alias}"
                            )
                            # Map alias back to (table, field) for ResultMapper
                            alias_map[alias] = (target_table, target_field_name)
                        
                        # Build JOIN clause
                        join_clauses.append(
                            f"LEFT JOIN {target_table} ON "
                            f"{base_table}.{fk_field_name} = {target_table}.id"
                        )
            
            # Construct full SELECT with JOINs
            sql_parts.append(f"SELECT {', '.join(select_fields)} FROM {base_table}")
            sql_parts.extend(join_clauses)
        else:
            sql_parts = [f"SELECT * FROM {base_table}"]
        
        # WHERE clause
        if self.conditions:
            where_parts = []
            for i, cond in enumerate(self.conditions, 1):
                where_sql, where_params = self._build_condition(cond, i)
                where_parts.append(where_sql)
                params.extend(where_params)
            
            sql_parts.append("WHERE " + " AND ".join(where_parts))
        
        # ORDER BY
        if self.order_fields:
            order_parts = []
            for field in self.order_fields:
                if field.startswith("-"):
                    order_parts.append(f"{field[1:]} DESC")
                else:
                    order_parts.append(f"{field} ASC")
            sql_parts.append("ORDER BY " + ", ".join(order_parts))
        
        # LIMIT
        if self.limit_value:
            sql_parts.append(f"LIMIT {self.limit_value}")
        
        # OFFSET
        if self.offset_value:
            sql_parts.append(f"OFFSET {self.offset_value}")
        
        sql = " ".join(sql_parts)
        return sql, params, alias_map
    
    def _build_condition(self, query: Query, param_index: int) -> tuple[str, List[Any]]:
        """Build single WHERE condition."""
        field = query.field
        operator = query.operator
        value = query.value
        
        if operator == "exact":
            return f"{field} = ${param_index}", [value]
        
        elif operator == "not_exact":
            return f"{field} != ${param_index}", [value]
        
        elif operator == "icontains":
            return f"{field} ILIKE ${param_index}", [f"%{value}%"]
        
        elif operator == "startswith":
            return f"{field} ILIKE ${param_index}", [f"{value}%"]
        
        elif operator == "endswith":
            return f"{field} ILIKE ${param_index}", [f"%{value}"]
        
        elif operator == "gte":
            return f"{field} >= ${param_index}", [value]
        
        elif operator == "lte":
            return f"{field} <= ${param_index}", [value]
        
        elif operator == "gt":
            return f"{field} > ${param_index}", [value]
        
        elif operator == "lt":
            return f"{field} < ${param_index}", [value]
        
        elif operator == "in":
            placeholders = ", ".join([f"${param_index + i}" for i in range(len(value))])
            return f"{field} IN ({placeholders})", list(value)
        
        elif operator == "isnull":
            if value:
                return f"{field} IS NULL", []
            else:
                return f"{field} IS NOT NULL", []
        
        else:
            raise ValueError(f"Unknown operator: {operator}")
    
    async def all(self) -> List[Any]:
        """Execute query and return all results."""
        sql, params, alias_map = self._build_sql()
        
        logger.debug(f"QUERY: {sql} | PARAMS: {params}")
        
        async with await get_session() as session:
            rows = await session.fetch(sql, *params)
        
            results = []
            for row in rows:
                mapped = ResultMapper.map_row(dict(row), self.model_class, self.model_class.__fields__, alias_map=alias_map)
                results.append(mapped)
        
        return results
    
    async def first(self) -> Optional[Any]:
        """Execute query and return first result."""
        # Add LIMIT 1
        self.limit_value = 1
        
        sql, params, alias_map = self._build_sql()
        
        logger.debug(f"QUERY: {sql} | PARAMS: {params}")
        
        async with await get_session() as session:
            row = await session.fetchrow(sql, *params)
        
        if row:
            return ResultMapper.map_row(dict(row), self.model_class, self.model_class.__fields__, alias_map=alias_map)
        
        return None
    
    async def count(self) -> int:
        """Get count without offset/limit."""
        # Build count query
        params: List[Any] = []
        sql_parts = [f"SELECT COUNT(*) FROM {self.model_class.__tablename__}"]
        
        if self.conditions:
            where_parts = []
            for i, cond in enumerate(self.conditions, 1):
                where_sql, where_params = self._build_condition(cond, i)
                where_parts.append(where_sql)
                params.extend(where_params)
            
            sql_parts.append("WHERE " + " AND ".join(where_parts))
        
        sql = " ".join(sql_parts)
        
        logger.debug(f"COUNT QUERY: {sql} | PARAMS: {params}")
        
        async with await get_session() as session:
            result = await session.fetchval(sql, *params)
        
        return result or 0
    
    async def exists(self) -> bool:
        """Check if any record matches."""
        result = await self.first()
        return result is not None
    
    async def paginate(self, page: int = 1, per_page: int = 10) -> "Page":
        """Paginate results."""
        from .pagination import Page
        
        # Calculate offset
        offset = (page - 1) * per_page
        self.offset_value = offset
        self.limit_value = per_page
        
        # Get total count
        total = await self.count()
        
        # Get page results
        items = await self.all()
        
        # Create Page object
        page_obj = Page(
            items=items,
            page=page,
            per_page=per_page,
            total=total,
        )
        
        return page_obj


class QuerySet:
    """
    Entry point for building queries on a model.
    
    Usage:
        posts = await Post.filter(is_published=True).order_by("-created_at").all()
    """
    
    def __init__(self, model_class: Type):
        self.model_class = model_class
    
    def filter(self, **kwargs) -> FilterChain:
        """Start filtering."""
        chain = FilterChain(model_class=self.model_class)
        return chain.filter(**kwargs)
    
    def exclude(self, **kwargs) -> FilterChain:
        """Start with exclusion filter."""
        chain = FilterChain(model_class=self.model_class)
        return chain.exclude(**kwargs)
    
    def all(self) -> FilterChain:
        """Return all records."""
        return FilterChain(model_class=self.model_class)


# Add QuerySet methods to Model
def add_queryset_methods(model_class):
    """Add QuerySet methods to model class."""
    
    @classmethod
    def filter(cls, **kwargs) -> FilterChain:
        chain = FilterChain(model_class=cls)
        return chain.filter(**kwargs)
    
    @classmethod
    def exclude(cls, **kwargs) -> FilterChain:
        chain = FilterChain(model_class=cls)
        return chain.exclude(**kwargs)
    
    model_class.filter = filter
    model_class.exclude = exclude
