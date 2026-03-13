"""
Eden ORM - Query Executor

Handles SQL execution, result mapping, and query optimization.
"""

from typing import Any, List, Dict, Optional, Type, Tuple
import logging
from datetime import datetime, date, time
from uuid import UUID
import json

logger = logging.getLogger(__name__)


class SQLBuilder:
    """
    Builds SQL queries programmatically.
    
    Provides safe parameter binding to prevent SQL injection.
    """
    
    def __init__(self):
        self.parts: List[str] = []
        self.params: List[Any] = []
        self.param_counter = 1
    
    def add_select(self, *fields: str) -> "SQLBuilder":
        """Add SELECT clause."""
        self.parts.append(f"SELECT {', '.join(fields)}")
        return self
    
    def add_from(self, table: str) -> "SQLBuilder":
        """Add FROM clause."""
        self.parts.append(f"FROM {table}")
        return self
    
    def add_where(self, condition: str, *args) -> "SQLBuilder":
        """Add WHERE clause with parameter binding."""
        self.parts.append(f"WHERE {condition}")
        self.params.extend(args)
        return self
    
    def add_and(self, condition: str, *args) -> "SQLBuilder":
        """Add AND to WHERE clause."""
        self.parts.append(f"AND {condition}")
        self.params.extend(args)
        return self
    
    def add_or(self, condition: str, *args) -> "SQLBuilder":
        """Add OR to WHERE clause."""
        self.parts.append(f"OR {condition}")
        self.params.extend(args)
        return self
    
    def add_insert(self, table: str, columns: List[str]) -> "SQLBuilder":
        """Add INSERT clause."""
        cols = ", ".join(columns)
        placeholders = ", ".join([f"${i}" for i in range(1, len(columns) + 1)])
        self.parts.append(f"INSERT INTO {table} ({cols}) VALUES ({placeholders})")
        self.param_counter = len(columns) + 1
        return self
    
    def add_update(self, table: str) -> "SQLBuilder":
        """Add UPDATE clause."""
        self.parts.append(f"UPDATE {table} SET")
        return self
    
    def add_set(self, columns: Dict[str, Any]) -> "SQLBuilder":
        """Add SET clause for UPDATE."""
        sets = []
        for col, val in columns.items():
            sets.append(f"{col} = ${self.param_counter}")
            self.params.append(val)
            self.param_counter += 1
        
        if self.parts[-1].endswith("SET"):
            self.parts[-1] += " " + ", ".join(sets)
        else:
            self.parts.append(", ".join(sets))
        
        return self
    
    def add_delete(self, table: str) -> "SQLBuilder":
        """Add DELETE clause."""
        self.parts.append(f"DELETE FROM {table}")
        return self
    
    def add_order_by(self, *fields: str) -> "SQLBuilder":
        """Add ORDER BY clause."""
        self.parts.append(f"ORDER BY {', '.join(fields)}")
        return self
    
    def add_limit(self, limit: int) -> "SQLBuilder":
        """Add LIMIT clause."""
        self.parts.append(f"LIMIT {limit}")
        return self
    
    def add_offset(self, offset: int) -> "SQLBuilder":
        """Add OFFSET clause."""
        self.parts.append(f"OFFSET {offset}")
        return self
    
    def add_join(self, join_type: str, table: str, on: str) -> "SQLBuilder":
        """Add JOIN clause."""
        self.parts.append(f"{join_type} JOIN {table} ON {on}")
        return self
    
    def build(self) -> Tuple[str, Tuple]:
        """Build final SQL query with parameters."""
        sql = " ".join(self.parts)
        return sql, tuple(self.params)


class ResultMapper:
    """Maps database rows to model instances."""
    
    @staticmethod
    def map_row(row: Dict[str, Any], model_class: Type, fields_map: Dict, alias_map: Dict[str, tuple[str, str]] = None) -> Any:
        """
        Map a database row to a model instance, including joined related objects.
        
        Args:
            row: Dictionary row from database
            model_class: The model class to instantiate
            fields_map: Map of field names to Field descriptors
            alias_map: Map of "table_column" -> ("table", "column") for deserialization
        
        Returns:
            Model instance with values populated (including related objects if alias_map provided)
        """
        instance = object.__new__(model_class)
        instance.__dict__ = {}
        related_data: Dict[str, Dict[str, Any]] = {}  # table -> {field: value}
        
        base_table = getattr(model_class, '__tablename__', model_class.__name__.lower())
        
        # Separate main table columns from joined table columns
        for col_name, value in row.items():
            if col_name in fields_map or col_name == 'id':
                # Base table column - set directly on instance
                if col_name in fields_map:
                    field = fields_map[col_name]
                    instance.__dict__[col_name] = ResultMapper.convert_value(
                        value, field.python_type
                    )
                else:
                    instance.__dict__[col_name] = value
            elif alias_map and col_name in alias_map:
                # Aliased column from joined table
                table_name, field_name = alias_map[col_name]
                if table_name not in related_data:
                    related_data[table_name] = {}
                related_data[table_name][field_name] = value
            else:
                # Unaliased column (shouldn't happen with new query builder)
                instance.__dict__[col_name] = value
        
        # Build related objects from joined data
        if related_data:
            for table_name, col_dict in related_data.items():
                # Find the relationship field that maps to this table
                for field_name, field in fields_map.items():
                    if field_name.endswith("_id") and hasattr(field, "to_model"):
                        related_model = field.to_model
                        if related_model.__tablename__ == table_name:
                            # Found the right relationship field
                            try:
                                # Create related object with deserialized data
                                rel_instance = object.__new__(related_model)
                                rel_instance.__dict__ = col_dict
                                
                                # Cache as private attribute for lazy loading to find later
                                rel_attr_name = field_name[:-3]  # Strip '_id' suffix
                                cache_attr = f"_cached_{rel_attr_name}"
                                setattr(instance, cache_attr, rel_instance)
                            except Exception as e:
                                logger.error(f"Failed to deserialize related {table_name}: {e}")
        
        return instance
    
    @staticmethod
    def convert_value(value: Any, target_type: Type) -> Any:
        """Convert database value to Python type."""
        if value is None:
            return None
        
        # JSON
        if target_type == dict and isinstance(value, str):
            return json.loads(value)
        
        # UUID
        if target_type == UUID and isinstance(value, str):
            return UUID(value)
        
        # DateTime
        if target_type == datetime and isinstance(value, str):
            return datetime.fromisoformat(value)
        
        # Date
        if target_type == date and isinstance(value, str):
            return date.fromisoformat(value)
        
        # Time
        if target_type == time and isinstance(value, str):
            return time.fromisoformat(value)
        
        return value


class QueryExecutor:
    """Executes queries and manages results."""
    
    def __init__(self, session):
        self.session = session
    
    async def execute_select(
        self,
        query: str,
        params: Tuple = (),
        model_class: Optional[Type] = None,
        fields_map: Optional[Dict] = None,
    ) -> List[Any]:
        """
        Execute SELECT query and return results.
        
        Returns list of model instances if model_class provided, else raw dicts.
        """
        rows = await self.session.fetch(query, *params)
        
        if model_class and fields_map:
            return [
                ResultMapper.map_row(dict(row), model_class, fields_map)
                for row in rows
            ]
        
        return [dict(row) for row in rows]
    
    async def execute_select_one(
        self,
        query: str,
        params: Tuple = (),
        model_class: Optional[Type] = None,
        fields_map: Optional[Dict] = None,
    ) -> Optional[Any]:
        """Execute SELECT query and return first result or None."""
        row = await self.session.fetchrow(query, *params)
        
        if row is None:
            return None
        
        if model_class and fields_map:
            return ResultMapper.map_row(dict(row), model_class, fields_map)
        
        return dict(row)
    
    async def execute_scalar(self, query: str, params: Tuple = ()) -> Any:
        """Execute query and return single scalar value."""
        return await self.session.fetchval(query, *params)
    
    async def execute_insert(self, query: str, params: Tuple = ()) -> None:
        """Execute INSERT query."""
        await self.session.execute(query, *params)
    
    async def execute_update(self, query: str, params: Tuple = ()) -> None:
        """Execute UPDATE query."""
        await self.session.execute(query, *params)
    
    async def execute_delete(self, query: str, params: Tuple = ()) -> None:
        """Execute DELETE query."""
        await self.session.execute(query, *params)


class QueryProfiler:
    """Profiles query execution for debugging."""
    
    def __init__(self, enable_logging: bool = False):
        self.enable_logging = enable_logging
        self.queries: List[Dict] = []
    
    def record_query(self, query: str, params: Tuple, duration: float) -> None:
        """Record executed query for analysis."""
        self.queries.append({
            "query": query,
            "params": params,
            "duration": duration,
        })
        
        if self.enable_logging:
            logger.debug(f"Query: {query} | Params: {params} | Duration: {duration}ms")
    
    def get_slow_queries(self, threshold_ms: float = 100) -> List[Dict]:
        """Get queries slower than threshold."""
        return [q for q in self.queries if q["duration"] > threshold_ms]
    
    def get_query_count(self) -> int:
        """Get total query count."""
        return len(self.queries)
    
    def reset(self) -> None:
        """Clear query history."""
        self.queries = []
