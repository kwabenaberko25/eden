from __future__ import annotations
"""
Eden — Database Lookups and Query Objects

Implements Django-style query capabilities:
- `Q` objects for complex AND/OR logic
- `F` expressions for column-level operations
- Lookup parsing (e.g., `title__icontains="Eden"`)
"""


import operator
from typing import Any, Callable, List, Dict, Type, Union, TYPE_CHECKING, TypeVar

from sqlalchemy import ColumnElement, and_, not_, or_, inspect as sa_inspect, func
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.orm.properties import ColumnProperty
from sqlalchemy.sql.elements import BinaryExpression, BindParameter
from sqlalchemy.sql.operators import custom_op
from sqlalchemy.orm.relationships import RelationshipProperty

_MISSING = object()

T = TypeVar('T')

# ── F Expressions ────────────────────────────────────────────────────────


class F:
    """
    References a column name for database-level operations.

    Usage:
        await User.filter(db, id=1).update(views=F("views") + 1)
    """

    def __init__(self, name: str) -> None:
        self.name = name

    def resolve(self, model: type[T]) -> Any:
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

    def resolve(self, model: type[T]) -> Any:
        return self.op(self.f_obj.resolve(model), self.other)


# ── Q Objects ────────────────────────────────────────────────────────────


class Q:
    """
    Q object for complex AND/OR/NOT logic.
    Supports both traditional __ syntax and new attribute-based lookups.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.kwargs = kwargs
        self._children: list[Any] = list(args)
        self._connector = operator.and_
        self._negated = False

    def __and__(self, other: Q) -> Q:
        return self._combine(other, operator.and_)

    def __or__(self, other: Q) -> Q:
        return self._combine(other, operator.or_)

    def __invert__(self) -> Q:
        new_q = self.copy()
        new_q._negated = not self._negated
        return new_q

    def _combine(self, other: Q, connector: Any) -> Q:
        new_q = Q()
        new_q._children = [self, other]
        new_q._connector = connector
        return new_q

    def copy(self) -> Q:
        new_q = Q()
        new_q.kwargs = self.kwargs.copy()
        new_q._children = self._children.copy()
        new_q._connector = self._connector
        new_q._negated = self._negated
        return new_q

    def resolve(self, model: type[T]) -> ColumnElement[bool]:
        """Convert this Q object into a SQLAlchemy boolean expression."""
        expressions: list[ColumnElement[bool]] = []

        # Resolve kwargs via the lookup parser (Legacy support)
        if self.kwargs:
            expressions.extend(parse_lookups(model, **self.kwargs))

        # Resolve children (New streamlined support)
        for child in self._children:
            if isinstance(child, Q):
                expressions.append(child.resolve(model))
            elif isinstance(child, LookupProxy):
                expressions.append(child.resolve(model))
            elif callable(child) and not isinstance(child, type):
                # Lambda support: filter(lambda u: u.name == '...')
                expressions.append(child(model))
            else:
                expressions.append(child)

        if not expressions:
            from sqlalchemy import true
            return true()

        clause = and_(*expressions) if self._connector == operator.and_ else or_(*expressions)
        return not_(clause) if self._negated else clause


# ── Streamlined Lookups & Proxy ──────────────────────────────────────────

class LookupProxy:
    """
    Captures attribute access and lookups for zero-boilerplate filtering.
    Used by the 'q' proxy.
    """
    def __init__(self, path: list[str], operator_name: str | None = None, value: Any = _MISSING):
        self._path = path
        self._operator_name = operator_name
        self._value = value

    def __getattr__(self, name: str) -> LookupProxy:
        return LookupProxy(self._path + [name])

    def _with_op(self, op: str, value: Any) -> LookupProxy:
        return LookupProxy(self._path, op, value)

    def icontains(self, value: Any) -> LookupProxy: return self._with_op("icontains", value)
    def contains(self, value: Any) -> LookupProxy: return self._with_op("contains", value)
    def startswith(self, value: Any) -> LookupProxy: return self._with_op("startswith", value)
    def istartswith(self, value: Any) -> LookupProxy: return self._with_op("istartswith", value)
    def endswith(self, value: Any) -> LookupProxy: return self._with_op("endswith", value)
    def iendswith(self, value: Any) -> LookupProxy: return self._with_op("iendswith", value)
    def isnull(self, value: bool = True) -> LookupProxy: return self._with_op("isnull", value)
    def in_(self, value: Any) -> LookupProxy: return self._with_op("in", value)
    def range(self, start: Any, end: Any) -> LookupProxy: return self._with_op("range", (start, end))

    # Standard operators
    def __eq__(self, value: Any) -> LookupProxy: return self._with_op("exact", value)
    def __ne__(self, value: Any) -> LookupProxy: return self._with_op("ne", value)
    def __gt__(self, value: Any) -> LookupProxy: return self._with_op("gt", value)
    def __ge__(self, value: Any) -> LookupProxy: return self._with_op("gte", value)
    def __lt__(self, value: Any) -> LookupProxy: return self._with_op("lt", value)
    def __le__(self, value: Any) -> LookupProxy: return self._with_op("lte", value)

    def resolve(self, model: type[T]) -> Any:
        # Resolve path to SQLAlchemy attribute
        attr = model
        for part in self._path:
            attr = getattr(attr, part)
        
        if self._operator_name is None:
            return attr
            
        kwargs = {f"{'__'.join(self._path)}__{self._operator_name}": self._value}
        return parse_lookups(model, **kwargs)[0]

# Universal Proxy Instance
q = LookupProxy([])


class EdenComparator(ColumnProperty.Comparator):
    """
    SQLAlchemy Comparator extension to add Django-style lookup methods 
    directly to model attributes (e.g. User.name.icontains("A")).
    """
    def icontains(self, other: Any):
        escaped = str(other).replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        return self.__clause_element__().ilike(f"%{escaped}%", escape="\\")

    def contains(self, other: Any):
        escaped = str(other).replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        return self.__clause_element__().like(f"%{escaped}%", escape="\\")

    def istartswith(self, other: Any):
        escaped = str(other).replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        return self.__clause_element__().ilike(f"{escaped}%", escape="\\")

    def startswith(self, other: Any):
        escaped = str(other).replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        return self.__clause_element__().like(f"{escaped}%", escape="\\")

    def iendswith(self, other: Any):
        escaped = str(other).replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        return self.__clause_element__().ilike(f"%{escaped}", escape="\\")

    def endswith(self, other: Any):
        escaped = str(other).replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        return self.__clause_element__().like(f"%{escaped}", escape="\\")

    def isnull(self, value: bool = True):
        return self.__clause_element__().is_(None) if value else self.__clause_element__().is_not(None)


class EdenRelationshipComparator(RelationshipProperty.Comparator):
    """
    SQLAlchemy Comparator for relationships to support nested attribute lookups
    (e.g., Product.category.name == "Electronics").
    """
    @property
    def property(self) -> Any:
        return self.prop

    def __getattr__(self, name: str) -> Any:
        # Avoid capturing special SQLAlchemy attributes or private attributes
        if name.startswith("_") or name in ("property", "comparator", "expression", "clause", "prop"):
            raise AttributeError(name)
        
        # Get the target model from the relationship property
        target_model = self.prop.mapper.class_
        # Return the attribute from the target model. 
        # This allows extract_involved_models to see the target column.
        return getattr(target_model, name)


def extract_involved_models(expression: Any) -> set[type[Any]]:
    """
    Inspects a SQLAlchemy/Eden expression to identify all involved Model classes.
    Used for automatic joining in QuerySet.filter().
    """
    from sqlalchemy.orm.attributes import InstrumentedAttribute
    from sqlalchemy.sql.visitors import iterate
    from sqlalchemy.sql.schema import Column
    from sqlalchemy.orm.util import AliasedClass
    
    models = set()
    
    if expression is None:
        return models

    # Iterate over all elements in the expression tree
    # Safety check: if it's a primitive or non-SQLAlchemy object, we can't iterate
    if hasattr(expression, "get_children"):
        for element in iterate(expression):
            # InstrumentedAttribute is what Model.column_name returns
            if isinstance(element, InstrumentedAttribute):
                if hasattr(element, "class_"):
                    models.add(element.class_)
            # AliasedClass (used in select_related/prefetch sometimes)
            elif isinstance(element, AliasedClass):
                from sqlalchemy import inspect as sa_inspect
                mapper = sa_inspect(element)
                if mapper:
                    models.add(mapper.class_)
            # Sometimes it's a Column bound to a table
            elif isinstance(element, Column) and hasattr(element, "table"):
                if hasattr(element.table, "name"):
                    # We need to find the Model class for this table
                    from .base import Model
                    for sub in Model.__subclasses__():
                        if getattr(sub, "__tablename__", None) == element.table.name:
                            models.add(sub)
                            break
            # Handle elements with .entity (SQLAlchemy 2.0 style)
            elif hasattr(element, "entity") and hasattr(element.entity, "class_"):
                models.add(element.entity.class_)
    
    # Handle direct attributes passed to filter
    elif isinstance(expression, InstrumentedAttribute):
        if hasattr(expression, "class_"):
            models.add(expression.class_)
            
    return models


def find_relationship_path(
    source_model: type[Any], 
    target_model: type[Any],
    max_depth: int = 5,
) -> list[str]:
    """
    Finds the shortest path of relationship names from source_model to target_model
    using Breadth-First Search (BFS) with depth limiting.
    
    Handles deep paths (e.g., GrandParent -> Parent -> Child).
    """
    from sqlalchemy import inspect as sa_inspect
    
    if source_model == target_model:
        return []
    
    # BFS queue: (current_model, path_list)
    import collections
    queue = collections.deque([(source_model, [])])
    visited = {source_model}
    
    while queue:
        current_model, path = queue.popleft()
        
        if len(path) >= max_depth:
            continue
        
        try:
            mapper = sa_inspect(current_model)
            if mapper is None:
                continue
            
            for rel in mapper.relationships:
                target = rel.mapper.class_
                
                new_path = path + [rel.key]
                if target == target_model:
                    return new_path
                
                if target not in visited:
                    visited.add(target)
                    queue.append((target, new_path))
                    
        except Exception:
            continue
    
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


def parse_lookups(model: type[T], **kwargs: Any) -> list[ColumnElement[bool]]:
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

        # Resolve F-expressions or Subqueries if passed as value
        from .query import QuerySet
        if isinstance(value, (F, _FExpr)):
            value = value.resolve(model)
        elif isinstance(value, QuerySet):
            # Automatic Subquery Promotion
            value = value.statement.scalar_subquery()

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
