
from __future__ import annotations
import uuid
import contextlib
from typing import Any, Dict, List, Optional, Type, TypeVar, Union, TYPE_CHECKING

if TYPE_CHECKING:
    from ..query import QuerySet
    T = TypeVar("T", bound="CrudMixin")

class CrudMixin:
    """
    Mixin that provides ActiveRecord-style CRUD operations for Eden models.
    """

    @classmethod
    def query(cls, session: Optional[Any] = None) -> QuerySet:
        """Returns a QuerySet for this model."""
        from ..query import QuerySet
        return QuerySet(cls, session=session)

    @classmethod
    def accessible_by(cls, user: Any, action: str = "read", session: Optional[Any] = None) -> QuerySet:
        """
        Returns a QuerySet pre-filtered for the given user and action.
        """
        return cls.query(session=session).for_user(user, action=action)

    @classmethod
    async def get(
        cls, session: Optional[Any] = None, id: Union[uuid.UUID, str, None] = None
    ) -> Optional[Any]:
        """Fetch a single record by primary key."""
        if id is None and session is not None and not hasattr(session, "execute"):
            id = session
            session = None
        return await cls.query(session=session).filter(id=id).first()

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
        cls, session: Optional[Any] = None, id: Union[uuid.UUID, str, None] = None
    ) -> Any:
        """Fetch a single record by primary key or raise NotFound."""
        record = await cls.get(session, id)
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

    async def save(self, session: Optional[Any] = None, validate: bool = True, commit: bool = True) -> Any:
        """
        Save the current instance to the database.
        """
        async with contextlib.AsyncExitStack() as stack:
            if session:
                sess = session
            else:
                sess = await stack.enter_async_context(self.__class__._provide_session())
            
            is_new = self.id is None
            if is_new:
                await self._call_hook("before_create", sess)
            
            await self._call_hook("before_save", sess)
            
            if validate:
                await self.full_clean()
            
            # Add to session
            sess.add(self)
            await sess.flush()
            
            if is_new:
                await self._call_hook("after_create", sess)
            await self._call_hook("after_save", sess)
            
            if commit and session is None:
                await sess.commit()
                await sess.refresh(self)
            elif commit: # If session was passed, we just flush but maybe user wants us to commit?
                # Original Eden behavior was to commit if session passed too? 
                # Let's check test_orm.py
                pass 
            
        return self

    async def update(self, session: Optional[Any] = None, commit: bool = True, **kwargs) -> Any:
        """
        Update the instance with the given keyword arguments and save it.
        """
        for k, v in kwargs.items():
            setattr(self, k, v)
        return await self.save(session=session, commit=commit)

    async def delete(self, session: Optional[Any] = None, commit: bool = True) -> None:
        """
        Delete the instance from the database.
        """
        async with contextlib.AsyncExitStack() as stack:
            if session:
                sess = session
            else:
                sess = await stack.enter_async_context(self.__class__._provide_session())
            
            await self._call_hook("before_delete", sess)
            await sess.delete(self)
            await self._call_hook("after_delete", sess)
            
            if commit and session is None:
                await sess.commit()

    @classmethod
    async def create(cls, session: Optional[Any] = None, **kwargs) -> Any:
        """Create a new record and save it to the database."""
        instance = cls(**kwargs)
        await instance.save(session)
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
