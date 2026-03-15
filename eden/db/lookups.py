"""
Eden — Database Lookups and Query Objects

Implements Django-style query capabilities:
- `Q` objects for complex AND/OR logic
- `F` expressions for column-level operations
- Lookup parsing (e.g., `title__icontains="Eden"`)
"""

from __future__ import annotations

import operator
from collections.abc import Callable
from typing import Any

from sqlalchemy import ColumnElement, and_, not_, or_

# ── F Expressions ────────────────────────────────────────────────────────


class F:
    """
    References a column name for database-level operations.

    Usage:
        await User.filter(db, id=1).update(views=F("views") + 1)
    """

    def __init__(self, name: str) -> None:
        self.name = name

    def resolve(self, model: type[Any]) -> Any:
        column = getattr(model, self.name, None)
        if column is None:
            raise ValueError(f"'{model.__name__}' has no column '{self.name}'")
        return column

    # Arithmetic operators
    def __add__(self, other: Any) -> _FExpr:
        return _FExpr(self, operator.add, other)

    def __sub__(self, other: Any) -> _FExpr:
        return _FExpr(self, operator.sub, other)

    def __mul__(self, other: Any) -> _FExpr:
        return _FExpr(self, operator.mul, other)

    def __truediv__(self, other: Any) -> _FExpr:
        return _FExpr(self, operator.truediv, other)


class _FExpr:
    """Internal class to represent an unresolved arithmetic expression on an F object."""

    def __init__(self, f_obj: F, op: Callable[..., Any], other: Any) -> None:
        self.f_obj = f_obj
        self.op = op
        self.other = other

    def resolve(self, model: type[Any]) -> Any:
        return self.op(self.f_obj.resolve(model), self.other)


# ── Q Objects ────────────────────────────────────────────────────────────


class Q:
    """
    Q object for complex AND/OR/NOT logic.

    Usage:
        await User.filter(db, Q(name__startswith="A") | ~Q(is_active=False))
    """

    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs
        self._children: list[Q | ColumnElement[Any]] = []
        self._connector = operator.and_
        self._negated = False

    def __and__(self, other: Q) -> Q:
        return self._combine(other, operator.and_)

    def __or__(self, other: Q) -> Q:
        return self._combine(other, operator.or_)

    def __invert__(self) -> Q:
        new_q = Q()
        new_q.kwargs = self.kwargs.copy()
        new_q._children = self._children.copy()
        new_q._connector = self._connector
        new_q._negated = not self._negated
        return new_q

    def _combine(self, other: Q, connector: Callable[..., Any]) -> Q:
        new_q = Q()
        new_q._children = [self.copy(), other.copy()]
        new_q._connector = connector
        return new_q

    def copy(self) -> Q:
        new_q = Q()
        new_q.kwargs = self.kwargs.copy()
        new_q._children = self._children.copy()
        new_q._connector = self._connector
        new_q._negated = self._negated
        return new_q

    def resolve(self, model: type[Any]) -> ColumnElement[bool]:
        """Convert this Q object into a SQLAlchemy boolean expression."""
        expressions: list[ColumnElement[bool]] = []

        # Resolve kwargs via the lookup parser
        if self.kwargs:
            expressions.extend(parse_lookups(model, **self.kwargs))

        # Resolve children
        for child in self._children:
            if isinstance(child, Q):
                expressions.append(child.resolve(model))
            else:
                # Support direct SQLAlchemy expressions passed as children
                expressions.append(child)

        if not expressions:
            from sqlalchemy import true
            return true()

        if self._connector == operator.and_:
            clause = and_(*expressions)
        else:
            clause = or_(*expressions)

        if self._negated:
            clause = not_(clause)

        return clause


def extract_involved_models(expression: Any) -> set[type[Any]]:
    """
    Inspects a SQLAlchemy/Eden expression to identify all involved Model classes.
    Used for automatic joining in QuerySet.filter().
    """
    from sqlalchemy.orm.attributes import InstrumentedAttribute
    from sqlalchemy.sql.visitors import iterate
    from sqlalchemy.sql.schema import Column
    
    models = set()
    
    # Iterate over all elements in the expression tree
    for element in iterate(expression):
        # InstrumentedAttribute is what Model.column_name returns
        if isinstance(element, InstrumentedAttribute):
            if hasattr(element, "class_"):
                models.add(element.class_)
        # Sometimes it's a Column bound to a table
        elif hasattr(element, "table") and hasattr(element.table, "name"):
            # We need to find the Model class for this table
            # This is harder, but Eden models are in the registry
            from .base import Model
            for sub in Model.__subclasses__():
                if getattr(sub, "__tablename__", None) == element.table.name:
                    models.add(sub)
                    break
        # Or it might have a .entity
        elif hasattr(element, "entity") and hasattr(element.entity, "class_"):
            models.add(element.entity.class_)
            
    return models


def find_relationship_path(
    source_model: type[Any], 
    target_model: type[Any],
    max_depth: int = 3,
) -> list[str]:
    """
    Finds the shortest path of relationship names from source_model to target_model
    using Breadth-First Search (BFS) with cycle detection and depth limiting.
    
    This function prevents stack overflows from circular relationships by:
    - Tracking visited models (cycle detection)
    - Limiting traversal depth (default: 3 levels)
    - Using BFS to find the shortest path (most efficient)
    
    Args:
        source_model: Starting model class
        target_model: Target model class to find path to
        max_depth: Maximum relationship depth to traverse (default: 3, prevents runaway traversal)
    
    Returns:
        List of relationship attribute names forming the path from source to target.
        Returns empty list if source == target.
        Returns empty list if no path found within max_depth.
        
    Raises:
        ValueError: If source_model or target_model cannot be inspected.
    
    Example:
        # Assuming: Author.books -> Book.publisher -> Publisher
        path = find_relationship_path(Author, Publisher)  # Returns ["books", "publisher"]
        # Then use: Author.books.property.mapper.class_.publisher
    """
    from sqlalchemy import inspect as sa_inspect
    
    # Early exit if they are the same
    if source_model == target_model:
        return []
    
    # BFS queue: (current_model, path_list, depth)
    queue = [(source_model, [], 0)]
    visited = {source_model}
    
    while queue:
        current_model, path, depth = queue.pop(0)
        
        # Check depth limit
        if depth > max_depth:
            continue
        
        # Early exit if we found the target
        if current_model == target_model:
            return path
        
        # Inspect relationships from current model
        try:
            mapper = sa_inspect(current_model)
            if mapper is None:
                continue
            
            for rel in mapper.relationships:
                target = rel.mapper.class_
                
                # Skip if already visited (cycle detection)
                if target not in visited:
                    visited.add(target)
                    new_path = path + [rel.key]
                    queue.append((target, new_path, depth + 1))
                    
        except Exception as e:
            # Log and skip non-mappable classes
            import logging
            logger = logging.getLogger("eden.db.lookups")
            logger.debug(f"Could not inspect relationships for {current_model.__name__}: {e}")
            continue
    
    # No path found within max_depth
    return []


# ── Lookup Parser ────────────────────────────────────────────────────────


SUPPORTED_LOOKUPS = {
    "exact",
    "iexact",
    "contains",
    "icontains",
    "startswith",
    "istartswith",
    "endswith",
    "iendswith",
    "gt",
    "gte",
    "lt",
    "lte",
    "in",
    "isnull",
    "range",
}


def parse_lookups(model: type[Any], **kwargs: Any) -> list[ColumnElement[bool]]:
    """
    Parse Django-style lookup strings into SQLAlchemy binary expressions.
    Supports recursive relationship traversal (e.g., `author__profile__name__icontains`).

    Supported lookups:
      - __exact (default)
      - __iexact
      - __contains
      - __icontains
      - __startswith / __istartswith
      - __endswith / __iendswith
      - __gt / __gte / __lt / __lte
      - __in
      - __isnull
      - __range
    """
    expressions: list[ColumnElement[bool]] = []

    for key, value in kwargs.items():
        parts = key.split("__")
        
        current_model = model
        column = None
        lookup = "exact"
        
        # Traverse relationships/fields
        for i, part in enumerate(parts):
            # Check if this part is an explicit lookup (must be the last part)
            if part in SUPPORTED_LOOKUPS and i == len(parts) - 1:
                lookup = part
                break
            
            # Get attribute from current_model
            attr = getattr(current_model, part, None)
            if attr is None:
                raise ValueError(f"'{current_model.__name__}' has no attribute '{part}'")
            
            # If it's a relationship, step into it
            if hasattr(attr, "property") and hasattr(attr.property, "mapper"):
                current_model = attr.property.mapper.class_
                # If this was the last part, we are matching against the relationship itself
                # (SQLAlchemy supports comparing relationship to instance or ID)
                if i == len(parts) - 1:
                    column = attr
                continue
            
            # It's a column (or some other descriptor)
            column = attr
            # Determine if the next part is a lookup
            if i == len(parts) - 2:
                next_part = parts[i+1]
                if next_part in SUPPORTED_LOOKUPS:
                    lookup = next_part
                    break
                else:
                    raise ValueError(f"Invalid lookup/field '{next_part}' after column '{part}'")
            elif i < len(parts) - 2:
                raise ValueError(f"Cannot traverse beyond column '{part}' in lookup path '{key}'")
            
            break # Found column/final target, end loop

        if column is None:
            raise ValueError(f"Could not resolve lookup path '{key}' on {model.__name__}")

        # Resolve F-expressions if passed as value
        if isinstance(value, (F, _FExpr)):
            value = value.resolve(model)

        # Handle string-to-UUID conversion for UUID columns
        from sqlalchemy import Uuid
        import uuid
        if isinstance(value, str) and isinstance(getattr(column, "type", None), Uuid):
            try:
                value = uuid.UUID(value)
            except (ValueError, AttributeError):
                pass # Let it fail or handle normally if not a valid UUID string

        if lookup == "exact":
            expr = column == value
        elif lookup == "iexact":
            expr = column.ilike(value)
        elif lookup == "contains":
            escaped_val = str(value).replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            expr = column.like(f"%{escaped_val}%", escape="\\")
        elif lookup == "icontains":
            escaped_val = str(value).replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            expr = column.ilike(f"%{escaped_val}%", escape="\\")
        elif lookup == "startswith":
            escaped_val = str(value).replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            expr = column.like(f"{escaped_val}%", escape="\\")
        elif lookup == "istartswith":
            escaped_val = str(value).replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            expr = column.ilike(f"{escaped_val}%", escape="\\")
        elif lookup == "endswith":
            escaped_val = str(value).replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            expr = column.like(f"%{escaped_val}", escape="\\")
        elif lookup == "iendswith":
            escaped_val = str(value).replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            expr = column.ilike(f"%{escaped_val}", escape="\\")
        elif lookup == "gt":
            expr = column > value
        elif lookup == "gte":
            expr = column >= value
        elif lookup == "lt":
            expr = column < value
        elif lookup == "lte":
            expr = column <= value
        elif lookup == "in":
            expr = column.in_(value)
        elif lookup == "isnull":
            expr = column.is_(None) if value else column.is_not(None)
        elif lookup == "range":
            # value must be (start, end)
            expr = column.between(value[0], value[1])
        else:
            raise ValueError(f"Unsupported lookup '{lookup}' on path '{key}'")

        expressions.append(expr)

    return expressions
