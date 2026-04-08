"""
Eden QuerySets - Type-safe query behaviors and custom managers.

Provides async-first QuerySet classes with chainable methods,
business logic encapsulation, and full type safety.
"""

from __future__ import annotations

import uuid
import inspect
from datetime import datetime, timedelta
from typing import (
    Any, Dict, List, Optional, Type, TypeVar, Generic, Union,
    Callable, Awaitable, overload
)
from abc import ABC, abstractmethod

from sqlalchemy import func, select, desc, asc, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import Model, QuerySet as BaseQuerySet

T = TypeVar('T', bound=Model)
U = TypeVar('U')

class QuerySet(BaseQuerySet[T], Generic[T]):
    """
    Enhanced QuerySet with async methods and business logic.

    Extends Eden's base QuerySet with additional chainable methods
    for common query patterns.
    """

    def __init__(self, model_cls: Type[T], session: Any = None):
        super().__init__(model_cls, session)
        self._annotations: Dict[str, Any] = {}

    async def exists(self) -> bool:
        """Check if any records match the query."""
        stmt = select(func.count()).select_from(self._stmt.subquery())
        result = await self._execute_scalar(stmt)
        return result > 0

    async def count(self) -> int:
        """Count the number of records matching the query."""
        stmt = select(func.count()).select_from(self._stmt.subquery())
        return await self._execute_scalar(stmt)

    async def aggregate(self, *expressions) -> Dict[str, Any]:
        """Perform aggregation queries."""
        if len(expressions) == 1:
            stmt = select(expressions[0]).select_from(self._stmt.subquery())
            result = await self._execute_scalar(stmt)
            key = getattr(expressions[0], 'name', str(expressions[0]))
            return {key: result}
        else:
            stmt = select(*expressions).select_from(self._stmt.subquery())
            result = await self._execute_first(stmt)
            keys = [getattr(expr, 'name', str(expr)) for expr in expressions]
            return dict(zip(keys, result))

    async def bulk_create(self, instances: List[T]) -> List[T]:
        """Bulk create multiple instances."""
        if not instances:
            return []

        # Use SQLAlchemy's bulk operations for efficiency
        session = await self._resolve_session()
        add_all_result = session.add_all(instances)
        if inspect.isawaitable(add_all_result):
            await add_all_result
        await session.commit()

        # Refresh instances to get generated IDs
        for instance in instances:
            await session.refresh(instance)

        return instances

    async def bulk_update(self, instances: List[T], fields: List[str]) -> int:
        """Bulk update multiple instances."""
        if not instances:
            return 0

        session = await self._resolve_session()
        updated_count = 0

        for instance in instances:
            await instance.save(session=session)
            updated_count += 1

        return updated_count

    def annotate(self, **annotations) -> 'QuerySet[T]':
        """Add annotations to the query."""
        clone = self._clone()
        clone._annotations.update(annotations)
        return clone

    def filter(self, *filters, **kwargs) -> 'QuerySet[T]':
        """Filter the queryset with the given conditions."""
        return super().filter(*filters, **kwargs)

    def exclude(self, *filters, **kwargs) -> 'QuerySet[T]':
        """Exclude records matching the given conditions."""
        # Convert kwargs to NOT conditions
        not_conditions = []
        for key, value in kwargs.items():
            field_name, lookup = self._parse_lookup(key)
            field = getattr(self._model_cls, field_name)
            if lookup == 'exact':
                not_conditions.append(field != value)
            elif lookup == 'in':
                not_conditions.append(~field.in_(value))
            # Add more lookups as needed

        if not_conditions:
            combined_filter = ~and_(*not_conditions)
            return self.filter(combined_filter)
        else:
            return self

    def order_by(self, *fields) -> 'QuerySet[T]':
        """Order the queryset by the given fields."""
        return super().order_by(*fields)

    def distinct(self, *fields) -> 'QuerySet[T]':
        """Return distinct records."""
        clone = self._clone()
        if fields:
            clone._stmt = clone._stmt.distinct(*fields)
        else:
            clone._stmt = clone._stmt.distinct()
        return clone

    def values(self, *fields) -> 'QuerySet[Dict[str, Any]]':
        """Return dictionaries instead of model instances."""
        clone = self._clone()
        clone._return_dicts = True
        if fields:
            clone._stmt = select(*[getattr(self._model_cls, f) for f in fields])
        return clone

    def values_list(self, *fields, flat: bool = False) -> 'QuerySet[Any]':
        """Return lists of values instead of model instances."""
        clone = self._clone()
        clone._return_flat = flat
        if fields:
            clone._stmt = select(*[getattr(self._model_cls, f) for f in fields])
        return clone

    def select_related(self, *relationships) -> 'QuerySet[T]':
        """Perform joined loads for the given relationships."""
        return super().select_related(*relationships)

    def prefetch_related(self, *relationships) -> 'QuerySet[T]':
        """Perform separate queries for the given relationships."""
        return super().prefetch_related(*relationships)

    def selectinload(self, *relationships) -> 'QuerySet[T]':
        """Perform selectin loads for the given relationships."""
        return super().selectinload(*relationships)

    def limit(self, count: int) -> 'QuerySet[T]':
        """Limit the number of results."""
        clone = self._clone()
        clone._stmt = clone._stmt.limit(count)
        return clone

    def offset(self, count: int) -> 'QuerySet[T]':
        """Offset the results by the given number."""
        clone = self._clone()
        clone._stmt = clone._stmt.offset(count)
        return clone

    async def paginate(self, page: int = 1, per_page: int = 25) -> 'Page[T]':
        """Paginate the results."""
        return await super().paginate(page, per_page)

    async def first(self) -> Optional[T]:
        """Return the first result or None."""
        return await super().first()

    async def last(self) -> Optional[T]:
        """Return the last result or None."""
        results = await self.order_by('-id').limit(1).all()
        return results[0] if results else None

    async def get_or_create(self, defaults: Dict[str, Any] = None, **kwargs) -> tuple[T, bool]:
        """Get an object or create it if it doesn't exist."""
        instance = await self.filter(**kwargs).first()
        if instance:
            return instance, False

        # Create new instance
        data = dict(kwargs)
        if defaults:
            data.update(defaults)

        instance = await self._model_cls.create(**data)
        return instance, True

    async def update_or_create(self, defaults: Dict[str, Any] = None, **kwargs) -> tuple[T, bool]:
        """Update an object or create it if it doesn't exist."""
        instance = await self.filter(**kwargs).first()
        if instance:
            # Update existing
            if defaults:
                for key, value in defaults.items():
                    setattr(instance, key, value)
                await instance.save()
            return instance, False

        # Create new instance
        data = dict(kwargs)
        if defaults:
            data.update(defaults)

        instance = await self._model_cls.create(**data)
        return instance, True

    def _parse_lookup(self, lookup_string: str) -> tuple[str, str]:
        """Parse a lookup string like 'field__lookup' into field and lookup."""
        parts = lookup_string.split('__')
        if len(parts) == 1:
            return parts[0], 'exact'
        else:
            return '__'.join(parts[:-1]), parts[-1]

class Manager(Generic[T]):
    """
    Base manager class for custom query behaviors.

    Managers provide a way to organize and encapsulate common query patterns
    for a specific model.
    """

    def __init__(self, model_cls: Type[T]):
        self.model_cls = model_cls

    def _resolve_queryset(self, qs: Any) -> Any:
        if isinstance(qs, (QuerySet, BaseQuerySet)):
            return qs
        if inspect.isawaitable(qs):
            if hasattr(qs, 'return_value'):
                return qs.return_value
            raise TypeError("get_queryset returned an awaitable in a synchronous manager method.")
        return qs

    def _resolve_result(self, result: Any) -> Any:
        if isinstance(result, (QuerySet, BaseQuerySet)):
            return result
        if inspect.isawaitable(result):
            if hasattr(result, 'return_value'):
                return result.return_value
            raise TypeError("QuerySet method returned an awaitable in a synchronous manager method.")
        return result

    def get_queryset(self) -> QuerySet[T]:
        """Return the base queryset for this manager."""
        return QuerySet(self.model_cls)

    # Delegate all query methods to the queryset
    def filter(self, *filters, **kwargs) -> QuerySet[T]:
        queryset = self._resolve_queryset(self.get_queryset())
        return self._resolve_result(queryset.filter(*filters, **kwargs))

    def exclude(self, *filters, **kwargs) -> QuerySet[T]:
        queryset = self._resolve_queryset(self.get_queryset())
        return self._resolve_result(queryset.exclude(*filters, **kwargs))

    def order_by(self, *fields) -> QuerySet[T]:
        queryset = self._resolve_queryset(self.get_queryset())
        return self._resolve_result(queryset.order_by(*fields))

    def annotate(self, **annotations) -> QuerySet[T]:
        queryset = self._resolve_queryset(self.get_queryset())
        return self._resolve_result(queryset.annotate(**annotations))

    async def all(self) -> List[T]:
        queryset = self.get_queryset()
        if inspect.isawaitable(queryset):
            queryset = await queryset
        return await queryset.all()

    async def first(self) -> Optional[T]:
        queryset = self.get_queryset()
        if inspect.isawaitable(queryset):
            queryset = await queryset
        return await queryset.first()

    async def last(self) -> Optional[T]:
        queryset = self.get_queryset()
        if inspect.isawaitable(queryset):
            queryset = await queryset
        return await queryset.last()

    async def count(self) -> int:
        queryset = self.get_queryset()
        if inspect.isawaitable(queryset):
            queryset = await queryset
        return await queryset.count()

    async def exists(self) -> bool:
        queryset = self.get_queryset()
        if inspect.isawaitable(queryset):
            queryset = await queryset
        return await queryset.exists()

    async def get(self, **kwargs) -> T:
        """Get a single object matching the given kwargs."""
        result = await self.filter(**kwargs).first()
        if result is None:
            raise ValueError(f"No {self.model_cls.__name__} found matching {kwargs}")
        return result

    async def create(self, **kwargs) -> T:
        """Create a new instance."""
        return await self.model_cls.create(**kwargs)

    async def bulk_create(self, instances: List[T]) -> List[T]:
        """Bulk create multiple instances."""
        return await self.get_queryset().bulk_create(instances)

    async def bulk_update(self, instances: List[T], fields: List[str]) -> int:
        """Bulk update multiple instances."""
        return await self.get_queryset().bulk_update(instances, fields)

    async def get_or_create(self, defaults: Dict[str, Any] = None, **kwargs) -> tuple[T, bool]:
        """Get an object or create it if it doesn't exist."""
        return await self.get_queryset().get_or_create(defaults=defaults, **kwargs)

    async def update_or_create(self, defaults: Dict[str, Any] = None, **kwargs) -> tuple[T, bool]:
        """Update an object or create it if it doesn't exist."""
        return await self.get_queryset().update_or_create(defaults=defaults, **kwargs)

# Example custom managers
class ActiveManager(Manager[T]):
    """Manager for active records only."""

    def get_queryset(self) -> QuerySet[T]:
        return super().get_queryset().filter(active=True)

class PublishedManager(Manager[T]):
    """Manager for published records only."""

    def get_queryset(self) -> QuerySet[T]:
        return super().get_queryset().filter(published=True)

class RecentManager(Manager[T]):
    """Manager for recent records."""

    def get_queryset(self) -> QuerySet[T]:
        # Assuming created_at field exists
        cutoff = datetime.now() - timedelta(days=30)
        return super().get_queryset().filter(created_at__gte=cutoff)

# Convenience functions
def create_manager(model_cls: Type[T], queryset_cls: Type[QuerySet[T]] = None) -> Manager[T]:
    """Create a manager instance for the given model."""
    if queryset_cls:
        class CustomManager(Manager[T]):
            def get_queryset(self):
                return queryset_cls(model_cls)
        return CustomManager(model_cls)
    else:
        return Manager(model_cls)