"""
Eden — QuerySet Interface

Provides a fluent, chainable API for building and executing database queries.
"""

from __future__ import annotations

from datetime import UTC
import contextlib
import asyncio
import random
from typing import TYPE_CHECKING, Any, Generic, TypeVar, List, Dict, Optional, Callable, Iterable, AsyncGenerator, AsyncIterator

from sqlalchemy import delete, select, update, func, select as sa_select
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from .utils import _MISSING
from eden.db.pagination import Page

if TYPE_CHECKING:
    from .session import Database

T = TypeVar("T", bound=Any)


class QuerySet(Generic[T]):
    """
    A chainable query builder for Eden models.

    Lazy evaluation: The query is only executed when a terminating method
    (like .all(), .first(), .count()) is called.
    """

    def __init__(self, model_cls: type[T], session: Any | None = _MISSING):
        self._model_cls = model_cls
        
        # Internal check for Database vs Session
        from eden.db.session import Database
        if isinstance(session, Database):
            model_cls._db = session
            self._session = _MISSING
        else:
            self._session = session
        # Start with the model's base select (respects SoftDeleteMixin if present)
        self._stmt = model_cls._base_select()
        self._prefetch_paths: list[str] = []
        self._select_related_paths: list[str] = []
        self._joined_models: set[type[Any]] = set()
        self._return_dicts: bool = False
        self._return_flat: bool = False
        self._annotations: dict[str, Any] = {}
        self._rbac_applied: bool = session is not _MISSING and session is not None # If session passed, assume context handled RBAC or it's internal
        self._cache_ttl: int | None = None

    def __await__(self):
        """Allows awaiting the QuerySet directly to call .all()"""
        return self.all().__await__()

    @property
    def has_session(self) -> bool:
        """Checks if a session is currently available without triggering acquisition."""
        return self._session is not None

    def _resolve_session_sync(self) -> "AsyncSession" | None:
        """
        Pure lookup for an existing session in current context.
        Returns None if no session found.
        """
        if self._session is not None and self._session is not _MISSING:
            return self._session

        from eden.db.session import get_session
        return get_session()

    def _clone(self) -> QuerySet[T]:
        """Create a copy of this QuerySet for safe chaining."""
        clone = QuerySet(self._model_cls, self._session)
        clone._stmt = self._stmt
        clone._prefetch_paths = self._prefetch_paths.copy()
        clone._select_related_paths = self._select_related_paths.copy()
        clone._joined_models = self._joined_models.copy()
        clone._return_dicts = self._return_dicts
        clone._return_flat = self._return_flat
        clone._annotations = self._annotations.copy()
        clone._rbac_applied = self._rbac_applied
        clone._cache_ttl = self._cache_ttl
        return clone

    @property
    def statement(self) -> Any:
        """
        Return the underlying SQLAlchemy statement.
        Use this to 'drop down' to raw SQLAlchemy power when needed.
        """
        return self._stmt

    # ── Chainable Methods ────────────────────────────────────────────────

    def filter(self, *args: Any, **kwargs: Any) -> QuerySet[T]:
        """Add filter conditions and return a new QuerySet with automatic joining."""
        from eden.db.lookups import Q, parse_lookups, extract_involved_models, find_relationship_path, LookupProxy
        from sqlalchemy.sql import ColumnElement

        clone = self._clone()
        expressions = []
        involved_models = set()

        # Handle positional arguments (Q objects, lambdas, Proxy lookups)
        for q_arg in args:
            if isinstance(q_arg, Q):
                expr = q_arg.resolve(self._model_cls)
                expressions.append(expr)
                involved_models.update(extract_involved_models(expr))
            elif isinstance(q_arg, LookupProxy):
                expr = q_arg.resolve(self._model_cls)
                expressions.append(expr)
                involved_models.update(extract_involved_models(expr))
            elif callable(q_arg) and not isinstance(q_arg, type):
                # Lambda support: .filter(lambda u: u.name == '...')
                # We pass a proxy or the model class?
                # Best is to pass the 'q' proxy but bound to this model's attributes conceptually,
                # or just pass the model class if developers use User.name.
                # If they use lambda u: u.name, 'u' will be the model class.
                expr = q_arg(self._model_cls)
                expressions.append(expr)
                involved_models.update(extract_involved_models(expr))
            elif isinstance(q_arg, ColumnElement):
                expressions.append(q_arg)
                involved_models.update(extract_involved_models(q_arg))
            else:
                expressions.append(q_arg)

        # Handle keyword lookups (Legacy system)
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
                    current_stmt = clone._stmt
                    current_model = self._model_cls
                    for segment in path:
                        rel_attr = getattr(current_model, segment)
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
        """Specify relationships to eager load (via separate SELECT)."""
        clone = self._clone()
        clone._prefetch_paths.extend(rels)
        return clone

    def select_related(self, *rels: str) -> QuerySet[T]:
        """Specify relationships to eager load (via SQL JOIN)."""
        clone = self._clone()
        clone._select_related_paths.extend(rels)
        return clone

    def order_by(self, *fields: str) -> QuerySet[T]:
        """Add sorting and return a new QuerySet."""
        clone = self._clone()
        for field in fields:
            desc = False
            if field.startswith("-"):
                field = field.removeprefix("-")
                desc = True

            column = getattr(self._model_cls, field, None)
            if column is None:
                # Check annotations
                column = self._annotations.get(field)
            
            if column is None:
                raise ValueError(f"'{self._model_cls.__name__}' has no field or annotation '{field}'")

            clone._stmt = clone._stmt.order_by(column.desc() if desc else column.asc())
        return clone

    def group_by(self, *fields: str) -> QuerySet[T]:
        """
        Group by the specified fields.
        Useful for aggregation across multiple columns.
        """
        clone = self._clone()
        for field in fields:
            column = getattr(self._model_cls, field, None)
            if column is None:
                column = self._annotations.get(field)
            
            if column is None:
                raise ValueError(f"'{self._model_cls.__name__}' has no field or annotation '{field}'")
            clone._stmt = clone._stmt.group_by(column)
        return clone

    def having(self, *args: Any, **kwargs: Any) -> QuerySet[T]:
        """
        Add HAVING conditions for aggregated queries.
        """
        from eden.db.lookups import Q, parse_lookups
        clone = self._clone()
        expressions = []
        
        for q in args:
            if isinstance(q, Q):
                expressions.append(q.resolve(self._model_cls))
            else:
                expressions.append(q)
                
        if kwargs:
            expressions.extend(parse_lookups(self._model_cls, **kwargs))
            
        if expressions:
            clone._stmt = clone._stmt.having(*expressions)
        return clone

    def values(self, *fields: str) -> "QuerySet[T]":
        """
        Return dictionaries containing only the specified fields.
        Note: Eager loading (prefetch/select_related) is not supported when using .values().
        """
        if self._prefetch_paths or self._select_related_paths:
            import logging
            logger = logging.getLogger("eden.db.query")
            logger.warning(
                f"QuerySet.values() called on {self._model_cls.__name__} after .prefetch() or .select_related(). "
                "SQLAlchemy does not support eager loading on scalar queries; related objects will not be included."
            )

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

    def values_list(self, *fields: str, flat: bool = False) -> QuerySet[Any]:
        """
        Similar to values(), but returns rows as tuples (or flat values if flat=True).
        """
        clone = self.values(*fields)
        # return_flat is handled in __aiter__ / all
        clone._return_flat = flat
        clone._return_dicts = False
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

    def cache(self, ttl: int = 300) -> QuerySet[T]:
        """
        Enable caching for this query.
        
        Args:
            ttl: Time to live in seconds (default: 300)
        """
        clone = self._clone()
        clone._cache_ttl = ttl
        return clone

    @contextlib.asynccontextmanager
    async def _provide_session(self) -> "AsyncGenerator[AsyncSession, None]":
        """
        Asynchronous context manager to resolve and provide a database session.
        Ensures that auto-acquired sessions are properly closed.
        """
        # 1. Use existing session lookup (explicit or context-aware)
        session = self._resolve_session_sync()
        if session:
            yield session
            return

        # 2. Fallback to model-bound database
        if self._model_cls._db is not None:
            async with self._model_cls._db.session() as session:
                yield session
                return

        # 3. Final error if no session could be resolved
        raise RuntimeError(
            "QuerySet requires a session for execution. "
            "Ensure one of:\n"
            f"  1) Call within request context or transaction\n"
            f"  2) Bind model to database: {self._model_cls.__name__}._bind_db(db)\n"
            f"  3) Pass session explicitly to .query(session=session)"
        )

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
        clone._rbac_applied = True
        return clone

    def _apply_rbac(self, action: str = "read") -> QuerySet[T]:
        """
        Automatically applies RBAC filters if enabled for the model and 
        a user is present in the current request context.
        """
        if self._rbac_applied:
            return self

        from eden.db.access import AccessControl
        if not issubclass(self._model_cls, AccessControl):
            return self

        from eden.context import get_user
        user = get_user()
        
        # Get security filters for the user (even if None)
        filters = self._model_cls.get_security_filters(user, action)
        
        if filters is False:
             # Access Denied: return a clone that will always be empty
             from sqlalchemy import text
             clone = self._clone()
             clone._stmt = clone._stmt.where(text("1=0"))
             clone._rbac_applied = True
             return clone
        
        if filters is True:
             # Full Access
             clone = self._clone()
             clone._rbac_applied = True
             return clone
             
        # Rule returned specific filters (e.g. Owner filter)
        clone = self._clone()
        clone._stmt = clone._stmt.where(filters)
        clone._rbac_applied = True
        return clone

    def search_ranked(self, query: str, fields: list[str] | None = None, language: str = "english") -> QuerySet[T]:
        """
        Perform a ranked search using PostgreSQL full-text search.
        Orders results by relevance.
        """
        from sqlalchemy import desc, func, inspect as sa_inspect
        from sqlalchemy.types import String, Text

        clone = self._clone()

        # Determine fields to search
        if not fields:
            fields = getattr(self._model_cls, "__search_fields__", None)

        if not fields:
            mapper = sa_inspect(self._model_cls)
            fields = [
                col.name
                for col in mapper.columns
                if isinstance(col.type, (String, Text))
            ]

        if not fields:
            raise ValueError(f"No searchable text fields found for {self._model_cls.__name__}")

        # Build search vector expression
        cols = [getattr(self._model_cls, f) for f in fields]

        # Use concat_ws to handle NULLs and combine fields
        concatenated = func.concat_ws(" ", *cols)
        search_vector = func.to_tsvector(language, concatenated)

        # Use plainto_tsquery for simple string input
        search_query = func.plainto_tsquery(language, query)

        # Apply filter and ranking
        clone._stmt = clone._stmt.where(search_vector.op("@@")(search_query))
        clone._stmt = clone._stmt.order_by(desc(func.ts_rank(search_vector, search_query)))

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
            from eden.db.aggregates import Aggregate, AggregateExpression

            # Use a subquery to wrap filters/joins before aggregating
            subq = self._stmt.subquery()
            sel_exprs = []
            
            for alias, agg in aggregates.items():
                if not hasattr(agg, "resolve"):
                    raise ValueError(f"Value for '{alias}' must be an Aggregate or AggregateExpression")
                
                # Resolve the aggregate using subquery columns
                expr = agg.resolve(self._model_cls, columns=subq.c)
                sel_exprs.append(expr.label(alias))

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

    def _apply_select_related(self, stmt):
        if not self._select_related_paths:
            return stmt

        for rel_path in self._select_related_paths:
            parts = rel_path.split(".")
            current_model = self._model_cls
            loader = None
            
            for part in parts:
                attr = getattr(current_model, part)
                if loader is None:
                    loader = joinedload(attr)
                else:
                    loader = loader.joinedload(attr)
                
                current_model = attr.property.mapper.class_
            
            if loader:
                stmt = stmt.options(loader)
        return stmt

    def _get_cache_key(self) -> str:
        """Generate a unique cache key for the current statement."""
        import hashlib
        from eden.context import get_user, get_tenant_id

        # Query-specific base derived from SQLAlchemy statement
        stmt_str = str(self._stmt.compile(compile_kwargs={"literal_binds": True}))

        # Context matters in RBAC / multi-tenant scenarios.
        tenant_id = get_tenant_id() or ""
        user = get_user()
        user_id = ""
        if user is not None:
            user_id = str(getattr(user, "id", user))

        key_raw = (
            f"{self._model_cls.__name__}:"
            f"{tenant_id}:"
            f"{user_id}:"
            f"{stmt_str}:"
            f"{self._prefetch_paths}:"
            f"{self._return_dicts}"
        )
        return f"qs:{hashlib.md5(key_raw.encode()).hexdigest()}"

    async def _execute(self, stmt: Any, session: "AsyncSession") -> Any:
        """
        Executes a statement with exponential backoff retries for reliability.
        """
        max_retries = 3
        base_delay = 0.1  # 100ms
        
        for attempt in range(max_retries + 1):
            try:
                return await session.execute(stmt)
            except Exception as e:
                # Only retry on potentially transient errors (connection, lock timeout)
                if attempt == max_retries:
                    raise e
                
                # Exponential backoff: base * 2^attempt + jitter
                delay = (base_delay * (2 ** attempt)) + (random.random() * 0.1)
                await asyncio.sleep(delay)

    async def __aiter__(self) -> "AsyncIterator[T]":
        """Allows async iteration over the QuerySet results."""
        results = await self.all()
        for res in results:
            yield res

    async def all(self) -> list[T]:
        """Execute query and return all results. Checks cache if enabled."""
        qs = self._apply_rbac("read")
        
        # Check cache if enabled
        cache_key = None
        if qs._cache_ttl is not None:
            from eden.context import get_app
            app = get_app()
            if app and hasattr(app, "cache"):
                cache_key = qs._get_cache_key()
                cached = await app.cache.get(cache_key)
                if cached is not None:
                    return cached

        async with qs._provide_session() as session:
            stmt = qs._apply_prefetch(qs._stmt)
            stmt = qs._apply_select_related(stmt)
            result = await self._execute(stmt, session)
            result = result.unique()
            
            records = []
            if getattr(self, "_return_dicts", False):
                for row in result:
                    obj = row[0]
                    if isinstance(obj, self._model_cls):
                        if hasattr(obj, "to_dict"):
                            records.append(obj.to_dict())
                        else:
                            records.append(obj)
                    else:
                        records.append(dict(row._mapping))
            elif getattr(self, "_return_flat", False):
                records = [row[0] for row in result]
            else:
                 records = list(result.scalars().all())
            
            # Store in cache if enabled
            if cache_key and app and hasattr(app, "cache"):
                await app.cache.set(cache_key, records, ttl=qs._cache_ttl)
                
            return records

    async def first(self) -> T | None:
        """Execute query and return the first result, or None."""
        qs = self._apply_rbac("read")
        async with qs._provide_session() as session:
            stmt = qs._apply_prefetch(qs._stmt)
            stmt = qs._apply_select_related(stmt)
            result = await self._execute(stmt, session)
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
            result = await self._execute(count_stmt, session)
            return result.scalar() or 0

    async def exists(self) -> bool:
        """Return True if any records match the query."""
        async with self._provide_session() as session:
            # Optimize exists by using limit(1)
            stmt = self._stmt.limit(1)
            result = await self._execute(stmt, session)
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
        Warning: Bypasses Model instance hooks and soft delete.
        """
        # Ensure we have a database
        db = self._model_cls._db
        if db is None:
            raise RuntimeError(f"Model {self._model_cls.__name__} is not bound to a database.")

        # Use transaction layer (will join existing or start new)
        async with db.transaction() as session:
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

            # Trigger signals
            from eden.db.signals import pre_bulk_update, post_bulk_update
            await pre_bulk_update.send(sender=self._model_cls, instance=self, values=values)

            # Build update statement: manually construct to ensure it applies to QuerySet's filters
            from sqlalchemy import update as sqla_update
            upd_stmt = sqla_update(self._model_cls)
            
            # Apply filters from current QuerySet
            if self._stmt._where_criteria:
                upd_stmt = upd_stmt.where(*self._stmt._where_criteria)
            
            upd_stmt = upd_stmt.values(**values)
            result = await session.execute(upd_stmt)

            if hasattr(self._model_cls, "after_bulk_update"):
                await self._model_cls.after_bulk_update(session, self, values, result.rowcount)
            
            await post_bulk_update.send(sender=self._model_cls, instance=self, values=values, count=result.rowcount)
            
            # Note: No explicit commit() here! db.transaction() handles it.
            return result.rowcount

    async def delete(self, hard: bool = False) -> int:
        """
        Perform a bulk delete on the matching records.
        If hard=False and model has SoftDeleteMixin, performs a soft delete.
        """
        db = self._model_cls._get_db()
        async with db.transaction(session=self._session) as session:
            # Check for soft delete
            if hasattr(self._model_cls, "deleted_at") and not hard:
                from datetime import datetime
                return await self.update(deleted_at=datetime.now(UTC))

            # Trigger hooks
            if hasattr(self._model_cls, "before_bulk_delete"):
                await self._model_cls.before_bulk_delete(session, self)

            # Trigger signals
            from eden.db.signals import pre_bulk_delete, post_bulk_delete
            await pre_bulk_delete.send(sender=self._model_cls, instance=self)

            # Build delete statement
            del_stmt = delete(self._model_cls)
            if self._stmt._where_criteria:
                del_stmt = del_stmt.where(*self._stmt._where_criteria)

            result = await session.execute(del_stmt)

            if hasattr(self._model_cls, "after_bulk_delete"):
                await self._model_cls.after_bulk_delete(session, self, result.rowcount)
            
            await post_bulk_delete.send(sender=self._model_cls, instance=self, count=result.rowcount)
            
            # Note: No explicit commit() here! db.transaction() handles it.
            return result.rowcount

    async def get_or_404(self, **filters) -> T:
        """
        Fetch a single record matching filters.
        Raises NotFound (404) if no record matches.
        """
        from eden.exceptions import NotFound
        
        result = await self.filter(**filters).first()
        if result is None:
            raise NotFound(detail=f"{self._model_cls.__name__} matching query not found.")
        return result

    async def filter_one(self, **filters) -> T | None:
        """
        Fetch a single record matching filters.
        Returns None if no record matches, raises if multiple records match.
        """
        results = await self.filter(**filters).all()
        if len(results) > 1:
            raise ValueError(
                f"Expected 1 result, got {len(results)} for {self._model_cls.__name__} "
                f"with filters {filters}"
            )
        return results[0] if results else None

    async def get_or_create(self, defaults: dict | None = None, **filters) -> tuple[T, bool]:
        """
        Fetch or create a record.
        Returns (instance, created) where created is True if a new record was created.
        """
        db = self._model_cls._get_db()
        async with db.transaction(session=self._session) as session:
            # Try to get the record
            existing = await self.filter(**filters).first()
            if existing:
                return (existing, False)
            
            # Create new instance
            create_data = {**filters}
            if defaults:
                create_data.update(defaults)
            
            instance = self._model_cls(**create_data)
            session.add(instance)
            await session.flush()
            await session.refresh(instance)
            return (instance, True)

    async def bulk_create(self, objects: list[T], batch_size: int = 100) -> int:
        """
        Create multiple instances in batches.
        Returns the count of created objects.
        """
        db = self._model_cls._get_db()
        async with db.transaction(session=self._session) as session:
            count = 0
            for i in range(0, len(objects), batch_size):
                batch = objects[i : i + batch_size]
                for obj in batch:
                    session.add(obj)
                    count += 1
                await session.flush()
            
            # Note: No explicit commit() here! db.transaction() handles it.
            return count
