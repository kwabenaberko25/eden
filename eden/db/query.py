"""
Eden — QuerySet Interface

Provides a fluent, chainable API for building and executing database queries.
"""

from __future__ import annotations

from datetime import UTC
import contextlib
from typing import TYPE_CHECKING, Any, Generic, TypeVar, List, Dict, Optional

from sqlalchemy import delete, select, update, func
from sqlalchemy.orm import selectinload

from eden.db.base import _MISSING
from eden.db.pagination import Page

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T", bound=Any)


class QuerySet(Generic[T]):
    """
    A chainable query builder for Eden models.

    Lazy evaluation: The query is only executed when a terminating method
    (like .all(), .first(), .count()) is called.
    """

    def __init__(self, model_cls: type[T], session: AsyncSession | None = _MISSING):
        self._model_cls = model_cls
        self._session = session
        # Start with the model's base select (respects SoftDeleteMixin if present)
        self._stmt = model_cls._base_select()
        self._prefetch_paths: list[str] = []
        self._joined_models: set[type[Any]] = set()
        self._return_dicts: bool = False
        self._annotations: dict[str, Any] = {}

    def __await__(self):
        """Allows awaiting the QuerySet directly to call .all()"""
        return self.all().__await__()

    @property
    def has_session(self) -> bool:
        """Checks if a session is currently available without triggering acquisition."""
        return self._session is not None

    async def _resolve_session(self) -> AsyncSession:
        """Resolve the session, auto-acquiring from the model's bound DB if needed."""
        if self._session is not None and self._session is not _MISSING:
            return self._session

        # Try to get session from model's bound DB
        try:
            # We use an async context manager, but QuerySet methods usually
            # expect a session they don't own the lifecycle of if passed in.
            # If we auto-acquire, we need to be careful.
            # For now, we'll use the model's _get_session which is a context manager.
            # This means methods using _resolve_session might need to be context-aware
            # OR we change how QuerySet works.

            # Implementation decision: Model methods like .all() handle the context manager.
            # QuerySet.all() should also handle it if session is MISSING.
            raise RuntimeError(
                "QuerySet requires a session for execution. Pass a session to "
                "query(), or use model-level methods like Model.all() which "
                "auto-acquire sessions."
            )
        except Exception as e:
            raise RuntimeError(f"Could not resolve database session: {e}")

    def _clone(self) -> QuerySet[T]:
        """Create a copy of this QuerySet for safe chaining."""
        clone = QuerySet(self._model_cls, self._session)
        clone._stmt = self._stmt
        clone._prefetch_paths = self._prefetch_paths.copy()
        clone._joined_models = self._joined_models.copy()
        clone._return_dicts = self._return_dicts
        clone._annotations = self._annotations.copy()
        return clone

    # ── Chainable Methods ────────────────────────────────────────────────

    def filter(self, *args: Any, **kwargs: Any) -> QuerySet[T]:
        """Add filter conditions and return a new QuerySet with automatic joining."""
        from eden.db.lookups import Q, parse_lookups, extract_involved_models, find_relationship_path
        from sqlalchemy.sql import ColumnElement

        clone = self._clone()
        expressions = []
        involved_models = set()

        # Collect models from positional args (expressions or Q objects)
        for q in args:
            if isinstance(q, Q):
                expr = q.resolve(self._model_cls)
                expressions.append(expr)
                involved_models.update(extract_involved_models(expr))
            elif isinstance(q, ColumnElement):
                expressions.append(q)
                involved_models.update(extract_involved_models(q))
            else:
                # Allow bools (True/False)
                expressions.append(q)

        # Collect models from keyword lookups
        if kwargs:
            kw_exprs = parse_lookups(self._model_cls, **kwargs)
            expressions.extend(kw_exprs)
            for expr in kw_exprs:
                involved_models.update(extract_involved_models(expr))

        # Auto-join models that are not the base model
        for target_model in involved_models:
            if target_model != self._model_cls and target_model not in clone._joined_models:
                path = find_relationship_path(self._model_cls, target_model)
                if path:
                    # Apply joins for each segment of the path
                    current_stmt = clone._stmt
                    current_model = self._model_cls
                    for segment in path:
                        rel_attr = getattr(current_model, segment)
                        # Only join if this specific link isn't already tracked or part of a previous join
                        # For simplicity, we track the final target_model, but in deep paths 
                        # we should technically track each step.
                        current_stmt = current_stmt.join(rel_attr)
                        current_model = rel_attr.property.mapper.class_
                    
                    clone._stmt = current_stmt
                    clone._joined_models.add(target_model)

        if expressions:
            clone._stmt = clone._stmt.where(*expressions)
        return clone

    def exclude(self, **kwargs: Any) -> QuerySet[T]:
        """Add negative filter conditions and return a new QuerySet."""
        from sqlalchemy import not_

        from eden.db.lookups import parse_lookups

        clone = self._clone()
        expressions = parse_lookups(self._model_cls, **kwargs)
        if expressions:
            clone._stmt = clone._stmt.where(*(not_(expr) for expr in expressions))
        return clone

    def prefetch(self, *rels: str) -> QuerySet[T]:
        """Specify relationships to eager load."""
        clone = self._clone()
        clone._prefetch_paths.extend(rels)
        return clone

    def order_by(self, *fields: str) -> QuerySet[T]:
        """Add sorting and return a new QuerySet."""
        clone = self._clone()
        for field in fields:
            desc = False
            if field.startswith("-"):
                field = field[1:]
                desc = True

            column = getattr(self._model_cls, field, None)
            if column is None:
                # Check annotations
                column = self._annotations.get(field)
            
            if column is None:
                raise ValueError(f"'{self._model_cls.__name__}' has no field or annotation '{field}'")

            clone._stmt = clone._stmt.order_by(column.desc() if desc else column.asc())
        return clone

    def values(self, *fields: str) -> "QuerySet[T]":
        """
        Return dictionaries containing only the specified fields.
        """
        clone = self._clone()
        cols = []
        for field in fields:
            # We want the column object from the model
            col = getattr(self._model_cls, field, None)
            if col is None:
                # Check annotations
                col = self._annotations.get(field)
            
            if col is None:
                raise ValueError(f"'{self._model_cls.__name__}' has no field or annotation '{field}'")
            cols.append(col)
        
        # with_only_columns ensures only these columns are selected
        clone._stmt = clone._stmt.with_only_columns(*cols)
        clone._return_dicts = True
        return clone

    def limit(self, n: int) -> QuerySet[T]:
        """Add limit and return a new QuerySet."""
        clone = self._clone()
        clone._stmt = clone._stmt.limit(n)
        return clone

    def offset(self, n: int) -> QuerySet[T]:
        """Add offset and return a new QuerySet."""
        clone = self._clone()
        clone._stmt = clone._stmt.offset(n)
        return clone

    def for_user(self, user: Any, action: str = "read") -> QuerySet[T]:
        """
        Apply model-level RBAC filters if the model implements AccessControl.
        If the model does not implement AccessControl, no filters are applied.
        """
        from eden.db.access import AccessControl

        if not issubclass(self._model_cls, AccessControl):
            return self

        filters = self._model_cls.get_security_filters(user, action)
        
        # filters can be a SQLAlchemy expression or a boolean
        if filters is False:
            # Absolute deny: inject a filter that always fails
            from sqlalchemy import false
            return self.filter(false())
        
        if filters is True:
            # Absolute allow: no extra filters
            return self
            
        # Specific expression (e.g. col == user_id)
        clone = self._clone()
        clone._stmt = clone._stmt.where(filters)
        return clone

    # ── Aggregation & Annotation ──────────────────────────────────────────

    async def aggregate(self, **aggregates: Any) -> dict[str, Any]:
        """
        Execute the query and return a dictionary of aggregation results.

        Example:
            results = await Product.query().aggregate(total_stock=Sum("stock"), avg_price=Avg("price"))
            # returns {"total_stock": 100, "avg_price": 49.99}
        """
        async with self._provide_session() as session:
            from eden.db.aggregates import Aggregate

            # Use a subquery to wrap filters/joins before aggregating
            subq = self._stmt.subquery()
            sel_exprs = []
            
            for alias, agg in aggregates.items():
                if not isinstance(agg, Aggregate):
                    raise ValueError(f"Value for '{alias}' must be an Aggregate instance")
                
                # Attempt to find the column in the subquery
                column = getattr(subq.c, agg.field, None)
                
                if column is None:
                    # Heuristic: Check for column name in mapper if attribute name not found
                    from sqlalchemy import inspect as sa_inspect
                    mapper = sa_inspect(self._model_cls)
                    if agg.field in mapper.all_orm_descriptors:
                        desc = mapper.all_orm_descriptors[agg.field]
                        if hasattr(desc, "property") and hasattr(desc.property, "columns"):
                            col_name = desc.property.columns[0].name
                            column = getattr(subq.c, col_name, None)

                if column is None:
                    # Final debug/fallback: what columns ARE there?
                    cols = list(subq.c.keys()) if subq.c is not None else []
                    raise ValueError(
                        f"Field '{agg.field}' not found in subquery for {self._model_cls.__name__}. "
                        f"Available columns: {cols}"
                    )
                
                agg_func = getattr(func, agg.function.lower())
                expr = agg_func(column).label(alias)
                sel_exprs.append(expr)

            stmt = select(*sel_exprs)
            result = await session.execute(stmt)
            row = result.fetchone()
            
            if row:
                return dict(row._asdict())
            return {k: None for k in aggregates}

    def annotate(self, **annotations: Any) -> QuerySet[T]:
        """
        Add calculated fields to each object in the QuerySet.
        Supports simple expressions and Aggregate functions.

        Example:
            users = await User.query().annotate(post_count=Count("posts")).all()
            print(users[0].post_count)
        """
        from eden.db.aggregates import Aggregate
        from sqlalchemy import select as sa_select
        from sqlalchemy.orm import RelationshipProperty

        clone = self._clone()
        
        for alias, expr in annotations.items():
            if isinstance(expr, Aggregate):
                # Advanced: Check if field is a relationship
                attr = getattr(self._model_cls, expr.field, None)
                if attr is not None and hasattr(attr, "prop") and isinstance(attr.prop, RelationshipProperty):
                    from sqlalchemy import inspect as sa_inspect
                    from sqlalchemy import select as sa_select
                    
                    rel = attr.prop
                    target_model = rel.mapper.class_
                    
                    # Logic: select count(*) from target where target.fk == self.pk
                    pk_col = sa_inspect(self._model_cls).primary_key[0]
                    sub_stmt = sa_select(func.count()).select_from(target_model)
                    
                    found_fk = False
                    for col in target_model.__table__.columns:
                        for fk in col.foreign_keys:
                            if fk.references(self._model_cls.__table__.c.id):
                                sub_stmt = sub_stmt.where(col == self._model_cls.id)
                                found_fk = True
                                break
                        if found_fk: break
                    
                    annot_expr = sub_stmt.scalar_subquery().label(alias)
                else:
                    # Simple column aggregate
                    annot_expr = expr.resolve(self._model_cls).label(alias)
            else:
                # Direct expression (e.g. col1 + col2)
                if hasattr(expr, "label"):
                    annot_expr = expr.label(alias)
                else:
                    # It might be a boolean or literal that can't be labeled directly?
                    # SQLAlchemy expressions usually have .label()
                    annot_expr = expr
            
            clone._annotations[alias] = annot_expr
            clone._stmt = clone._stmt.add_columns(annot_expr)
        
        return clone

    # ── Terminating Methods (Execution) ──────────────────────────────────

    def _apply_prefetch(self, stmt):
        if not self._prefetch_paths:
            return stmt

        for rel_path in self._prefetch_paths:
            parts = rel_path.split(".")
            current_model = self._model_cls
            loader = None
            
            for part in parts:
                attr = getattr(current_model, part)
                if loader is None:
                    loader = selectinload(attr)
                else:
                    loader = loader.selectinload(attr)
                
                # Move to the target model for the next segment
                current_model = attr.property.mapper.class_
                
            if loader:
                stmt = stmt.options(loader)
        return stmt

    @contextlib.asynccontextmanager
    async def _provide_session(self):
        """Yields an active session, either provided or auto-acquired."""
        if self._session is not _MISSING and self._session is not None:
            yield self._session
        else:
            async with self._model_cls._get_session() as session:
                yield session

    async def all(self) -> list[T]:
        """Execute query and return all results."""
        async with self._provide_session() as session:
            stmt = self._apply_prefetch(self._stmt)
            result = await session.execute(stmt)
            result = result.unique()
            
            if getattr(self, "_return_dicts", False):
                records = []
                for row in result:
                    # SQLAlchemy result rows are tuple-like. 
                    # If it's a model-based QuerySet, row[0] might be the model instance.
                    obj = row[0]
                    if isinstance(obj, self._model_cls):
                        # Case 1: Full model instance returned as scalar
                        if hasattr(obj, "to_dict"):
                            records.append(obj.to_dict())
                        else:
                            records.append(obj)
                    else:
                        # Case 2: Specific columns selected (values() or results of grouping/agg)
                        # We use _mapping to get a dict representation of the row.
                        records.append(dict(row._mapping))
                return records
            
            # Default: return model instances
            return list(result.scalars().all())

    async def first(self) -> T | None:
        """Execute query and return the first result, or None."""
        async with self._provide_session() as session:
            stmt = self._apply_prefetch(self._stmt)
            result = await session.execute(stmt)
            result = result.unique()
            
            if getattr(self, "_return_dicts", False):
                row = result.first()
                if not row: return None
                
                obj = row[0]
                if isinstance(obj, self._model_cls):
                    if hasattr(obj, "to_dict"):
                        return obj.to_dict()
                    return obj
                else:
                    return dict(row._mapping)
            
            # Default: return model instance
            return result.scalars().first()

    async def last(self) -> T | None:
        """Execute query and return the last result."""
        results = await self.all()
        return results[-1] if results else None

    async def get(self, id: Any) -> T | None:
        """Fetch a single record by ID, respecting current filters."""
        async with self._provide_session() as session:
            # Handle string-to-UUID conversion for convenience (common in web apps)
            if isinstance(id, str) and hasattr(self._model_cls, "id"):
                col = getattr(self._model_cls, "id")
                from sqlalchemy import Uuid
                import uuid
                if hasattr(col, "type") and isinstance(col.type, Uuid):
                    try:
                        id = uuid.UUID(id)
                    except ValueError:
                        pass
            
            return await self.filter(id=id).first()

    async def count(self) -> int:
        """Return the number of matching records."""
        async with self._provide_session() as session:
            # Wrap the current statement in a subquery to count correctly
            count_stmt = select(func.count()).select_from(self._stmt.subquery())
            result = await session.execute(count_stmt)
            return result.scalar() or 0

    async def exists(self) -> bool:
        """Return True if any records match the query."""
        async with self._provide_session() as session:
            # Optimize exists by using limit(1)
            stmt = self._stmt.limit(1)
            result = await session.execute(stmt)
            return result.first() is not None

    async def paginate(self, page: int = 1, per_page: int = 20) -> Page[T]:
        """Return a Page object for the current query slice."""
        from eden.db.pagination import Page

        total = await self.count()
        items = await self.offset((page - 1) * per_page).limit(per_page).all()
        return Page(items=items, total=total, page=page, per_page=per_page)

    async def update(self, **kwargs: Any) -> int:
        """
        Perform a bulk update on the matching records.
        Warning: Bypasses Model instance hooks.
        """
        async with self._provide_session() as session:
            from eden.db.lookups import F, _FExpr
            
            # Resolve F-expressions
            values = {}
            for k, v in kwargs.items():
                if isinstance(v, (F, _FExpr)):
                    values[k] = v.resolve(self._model_cls)
                else:
                    values[k] = v

            # Trigger hooks if present
            if hasattr(self._model_cls, "before_bulk_update"):
                await self._model_cls.before_bulk_update(session, self, values)

            # Build update statement
            upd_stmt = update(self._model_cls)
            if self._stmt._where_criteria:
                upd_stmt = upd_stmt.where(*self._stmt._where_criteria)
            
            upd_stmt = upd_stmt.values(**values)
            result = await session.execute(upd_stmt)

            if hasattr(self._model_cls, "after_bulk_update"):
                await self._model_cls.after_bulk_update(session, self, values, result.rowcount)
            
            await session.commit()
            return result.rowcount

    async def delete(self, hard: bool = False) -> int:
        """
        Perform a bulk delete on the matching records.
        If hard=False and model has SoftDeleteMixin, performs a soft delete.
        """
        async with self._provide_session() as session:
            # Check for soft delete
            if hasattr(self._model_cls, "deleted_at") and not hard:
                from datetime import datetime
                return await self.update(deleted_at=datetime.now(UTC))

            # Trigger hooks
            if hasattr(self._model_cls, "before_bulk_delete"):
                await self._model_cls.before_bulk_delete(session, self)

            # Build delete statement
            del_stmt = delete(self._model_cls)
            if self._stmt._where_criteria:
                del_stmt = del_stmt.where(*self._stmt._where_criteria)

            result = await session.execute(del_stmt)

            if hasattr(self._model_cls, "after_bulk_delete"):
                await self._model_cls.after_bulk_delete(session, self, result.rowcount)
            
            await session.commit()
            return result.rowcount
