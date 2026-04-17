from __future__ import annotations
import logging
import inspect
from typing import TYPE_CHECKING, Any, Dict, Type, Optional

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("eden.db.context")

class BaseManager:
    """
    Base class for all domain-specific logic (actions/managers).
    
    A manager handles a specific domain area (e.g. Auth, Billing, Admin) 
    and is bound to a specific EdenDbContext (and thus a database session).
    """
    def __init__(self, ctx: EdenDbContext):
        self.ctx = ctx
        self.session = ctx.session

    def __repr__(self):
        return f"<{self.__class__.__name__} bound to session {id(self.session)}>"


class EdenDbContext:
    """
    The Unified Context for database operations.
    
    Provides explicit access to a database session and domain managers.
    Enforces transaction boundaries and multi-tenancy isolation.
    """
    
    # Global registry for auto-discovered managers
    # Map of name -> Manager class
    _registry: Dict[str, Type[BaseManager]] = {}

    def __init__(
        self, 
        session: AsyncSession, 
        tenant_id: Optional[str] = None, 
        user_id: Optional[Any] = None
    ):
        self.session = session
        self.tenant_id = tenant_id
        self.user_id = user_id
        self._instances: Dict[str, BaseManager] = {}

    @classmethod
    def register_manager(cls, name: str, manager_cls: Type[BaseManager]):
        """Explicitly register a manager (used by auto-discovery)."""
        cls._registry[name] = manager_cls
        logger.debug(f"Registered manager '{name}': {manager_cls.__name__}")

    def __getattr__(self, name: str) -> BaseManager:
        """
        Lazily initialize and return a registered manager.
        Allows access via ctx.users, ctx.auth, etc.
        """
        if name in self._registry:
            if name not in self._instances:
                manager_cls = self._registry[name]
                self._instances[name] = manager_cls(self)
            return self._instances[name]
        
        raise AttributeError(
            f"EdenDbContext has no manager named '{name}'. "
            f"Available managers: {list(self._registry.keys())}"
        )

    async def __aenter__(self) -> EdenDbContext:
        """Allow use as an async context manager."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Handle automatic cleanup/rollback if needed (though Database handles it)."""
        pass

    def get_manager(self, name: str) -> BaseManager:
        """Explicit getter for managers."""
        return getattr(self, name)
