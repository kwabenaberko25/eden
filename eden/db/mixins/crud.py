from __future__ import annotations

import uuid
import contextlib
from typing import Any, Dict, List, Optional, Type, TypeVar, Union, TYPE_CHECKING

from ..query import QuerySet

if TYPE_CHECKING:
    T = TypeVar("T", bound="CrudMixin")

class CrudMixin:
    """
    Mixin that provides ActiveRecord-style CRUD operations for Eden models.
    """

    @classmethod
    def query(cls, session: Optional[Any] = None, **kwargs) -> QuerySet:
        """Returns a QuerySet for this model."""
        from ..query import QuerySet
        return QuerySet(cls, session=session, **kwargs)

    @classmethod
    def include_tenantless(cls, session: Optional[Any] = None) -> QuerySet:
        """Helper to start a query that bypasses tenant isolation."""
        return cls.query(session=session, include_tenantless=True)

    @classmethod
    def without_rbac(cls, session: Optional[Any] = None) -> QuerySet:
        """
        Helper to start a query that explicitly bypasses RBAC security filters.
        Use with caution - intended for admin-level operations or background tasks.
        """
        return cls.query(session=session).bypass_rbac()

    @classmethod
    def accessible_by(cls, user: Any, action: str = "read", session: Optional[Any] = None) -> QuerySet:
        """
        Returns a QuerySet pre-filtered for the given user and action.
        """
        return cls.query(session=session).for_user(user, action=action)

    @classmethod
    async def get(
        cls, 
        *args,
        session: Optional[Any] = None, 
        id: Union[uuid.UUID, str, None] = None,
        **kwargs
    ) -> Optional[Any]:
        """
        Fetch a single record by primary key or by filter criteria.
        
        Preferred usage (explicit keyword):
            user = await User.get(id=user_id)
            user = await User.get(id=user_id, session=session)
        
        Legacy positional usage (still supported, but deprecated):
            user = await User.get(some_id)
        
        Filter by non-PK fields:
            user = await User.get(email="alice@example.com")
        
        Args:
            id: Primary key value to look up.
            session: Optional database session.
            **kwargs: Additional filter criteria (e.g., email="...").
        
        Returns:
            The model instance or None if not found.
        
        Raises:
            TypeError: If called with ambiguous positional arguments.
        """
        import warnings
        
        if args:
            if len(args) == 1:
                # Legacy positional: Model.get(some_id)
                # We treat the single positional arg as the ID
                if id is not None:
                    raise TypeError(
                        f"{cls.__name__}.get() received both a positional argument "
                        f"and id={id!r}. Use keyword argument only: "
                        f"{cls.__name__}.get(id=...)"
                    )
                warnings.warn(
                    f"{cls.__name__}.get(value) positional form is deprecated. "
                    f"Use {cls.__name__}.get(id=value) instead.",
                    FutureWarning,
                    stacklevel=2,
                )
                id = args[0]
            else:
                raise TypeError(
                    f"{cls.__name__}.get() takes at most 1 positional argument "
                    f"({len(args)} given). Use keyword arguments: "
                    f"{cls.__name__}.get(id=..., session=...)"
                )
        
        qs = cls.query(session=session)
        
        if id is not None:
            return await qs.filter(id=id).first()
        elif kwargs:
            return await qs.filter(**kwargs).first()
        else:
            raise TypeError(
                f"{cls.__name__}.get() requires at least an 'id' or filter criteria. "
                f"Usage: {cls.__name__}.get(id=...) or {cls.__name__}.get(email=...)"
            )

    @classmethod
    async def all(cls, *args, **kwargs) -> List[Any]:
        """Fetch all records."""
        session = kwargs.pop("session", None)
        if args and hasattr(args[0], "execute"):
            session = args[0]
            args = args[1:]

        qs = cls.query(session=session)
        prefetch = kwargs.pop("prefetch", None)
        if prefetch:
            qs = qs.prefetch(*prefetch)
        return await qs.all()

    @classmethod
    async def get_or_404(
        cls, *args, session: Optional[Any] = None, id: Union[uuid.UUID, str, None] = None
    ) -> Any:
        """Fetch a single record by primary key or raise NotFound."""
        record = await cls.get(*args, session=session, id=id)
        if not record:
            from eden.exceptions import NotFound
            raise NotFound(detail=f"{cls.__name__} with ID {id} not found.")
        return record

    @classmethod
    def filter(cls, *args, **kwargs) -> QuerySet:
        """Filter records."""
        session = kwargs.pop("session", None)
        if args and hasattr(args[0], "execute"):
            session = args[0]
            args = args[1:]

        qs = cls.query(session=session)
        prefetch = kwargs.pop("prefetch", None)
        if prefetch:
            qs = qs.prefetch(*prefetch)
        return qs.filter(*args, **kwargs)

    @classmethod
    def exclude(cls, *args, **kwargs) -> QuerySet:
        """Exclude records matching the criteria."""
        session = kwargs.pop("session", None)
        if args and hasattr(args[0], "execute"):
            session = args[0]
            args = args[1:]

        qs = cls.query(session=session)
        prefetch = kwargs.pop("prefetch", None)
        if prefetch:
            qs = qs.prefetch(*prefetch)
        return qs.exclude(*args, **kwargs)

    @classmethod
    def order_by(cls, *args, **kwargs) -> QuerySet:
        """Order records."""
        session = kwargs.pop("session", None)
        if args and hasattr(args[0], "execute"):
            session = args[0]
            args = args[1:]

        return cls.query(session=session).order_by(*args, **kwargs)

    @classmethod
    async def filter_one(cls, *args, **kwargs) -> Optional[Any]:
        """Fetch a single record matching the criteria."""
        return await cls.filter(*args, **kwargs).first()

    @classmethod
    async def count(cls, *args, **kwargs) -> int:
        """Return the total number of records matching the criteria."""
        return await cls.filter(*args, **kwargs).count()

    @classmethod
    async def paginate(cls, *args, **kwargs) -> Any:
        """Paginate records."""
        session = kwargs.pop("session", None)
        if args and hasattr(args[0], "execute"):
            session = args[0]
            args = args[1:]

        page = kwargs.pop("page", 1)
        per_page = kwargs.pop("per_page", 20)

        if len(args) > 0:
            page = args[0]
        if len(args) > 1:
            per_page = args[1]

        return await cls.filter(session=session, **kwargs).paginate(page, per_page)

    async def update(self, session: Optional[Any] = None, commit: bool = True, **kwargs) -> Any:
        """
        Update the instance with the given keyword arguments and save it.
        """
        for k, v in kwargs.items():
            setattr(self, k, v)
        # self.save() is provided by LifecycleMixin in the Model class
        return await self.save(session=session, commit=commit)

    @classmethod
    async def create(cls, session: Optional[Any] = None, commit: bool = True, validate: bool = True, **kwargs) -> Any:
        """
        Create a new record and save it to the database.
        
        Args:
            session: Optional existing session to use.
            commit: Whether to commit the transaction (default: True).
            validate: Whether to run validation before saving (default: True).
            **kwargs: Attributes for the new instance.
        """
        instance = cls(**kwargs)
        # Note: instance.save() is available via LifecycleMixin
        await instance.save(session=session, commit=commit, validate=validate)
        return instance

    @classmethod
    async def create_from(cls, source: Any, session: Optional[Any] = None) -> Any:
        """
        Create a new model instance from a validated Form, Schema, or dict.
        """
        if hasattr(source, "model_instance") and source.model_instance:
            data = source.model_instance.model_dump()
        elif hasattr(source, "model_dump"):
            data = source.model_dump()
        elif isinstance(source, dict):
            data = source
        else:
            raise TypeError(f"Cannot create {cls.__name__} from {type(source)}")

        from sqlalchemy import inspect
        mapper = inspect(cls)
        valid_keys = set(mapper.columns.keys()) | set(mapper.relationships.keys())
        filtered_data = {k: v for k, v in data.items() if k in valid_keys and k != "id"}

        return await cls.create(session=session, **filtered_data)

    async def update_from(self, source: Any, session: Optional[Any] = None) -> Any:
        """
        Update this model instance from a validated Form, Schema, or dict.
        """
        if hasattr(source, "model_instance") and source.model_instance:
            data = source.model_instance.model_dump()
        elif hasattr(source, "model_dump"):
            data = source.model_dump()
        elif isinstance(source, dict):
            data = source
        else:
            raise TypeError(f"Cannot update {self.__class__.__name__} from {type(source)}")

        from sqlalchemy import inspect
        mapper = inspect(self.__class__)
        valid_keys = set(mapper.columns.keys()) | set(mapper.relationships.keys())

        for k, v in data.items():
            if k in valid_keys and k != "id":
                setattr(self, k, v)

        await self.save(session)
        return self

    @classmethod
    async def get_or_create(
        cls, session: Optional[Any] = None, defaults: Optional[Dict[str, Any]] = None, **kwargs
    ) -> tuple[Any, bool]:
        """Fetch a record or create it if not found."""
        obj = await cls.filter_one(session=session, **kwargs)
        if obj:
            return obj, False

        params = {**kwargs, **(defaults or {})}
        return await cls.create(session=session, **params), True

    @classmethod
    async def update_or_create(
        cls, session: Optional[Any] = None, defaults: Optional[Dict[str, Any]] = None, **kwargs
    ) -> tuple[Any, bool]:
        """Update a record if it exists, otherwise create it."""
        obj = await cls.filter_one(session=session, **kwargs)
        if obj:
            if defaults:
                for k, v in defaults.items():
                    setattr(obj, k, v)
                await obj.save(session=session)
            return obj, False

        params = {**kwargs, **(defaults or {})}
        return await cls.create(session=session, **params), True
