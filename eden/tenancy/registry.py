"""
Eden — Tenancy Registry

Tracks models that require tenant isolation, even if they don't explicitly 
inherit from TenantMixin.
"""

import logging
import weakref
import os
from typing import Set, Type, Any

logger = logging.getLogger("eden.tenancy.registry")

class TenancyRegistry:
    """
    A central registry for all models in the framework that require 
    tenant-level isolation.
    """
    def __init__(self):
        # We store model names (strings) to avoid early import circularity,
        # and we can also store the actual weak references to classes if needed.
        self._isolated_models: Set[str] = set()
        # Enable strict mode by default if EDEN_STRICT_TENANCY is set
        self._strict_mode: bool = os.getenv("EDEN_STRICT_TENANCY", "false").lower() == "true"

    def register(self, model_cls: Any) -> None:
        """Register a model class as requiring tenant isolation."""
        # Honor explicit opt-out on the class if present
        if getattr(model_cls, "__tenant_isolated__", True) is False:
            logger.debug(f"Skipping registration for {model_cls.__name__} (explicitly disabled).")
            return

        name = model_cls.__name__
        if name not in self._isolated_models:
            logger.debug(f"Registering {name} as a tenant-isolated model.")
            self._isolated_models.add(name)

    def is_isolated(self, model_cls: Any) -> bool:
        """Check if a model class is registered for isolation."""
        # 1. Explicit opt-out on the class takes precedence
        if getattr(model_cls, "__tenant_isolated__", None) is False:
            return False

        # 2. Check by registered name
        if model_cls.__name__ in self._isolated_models:
            return True
        
        # 3. Fallback: check if it inherits from TenantMixin (if imported)
        # Note: TenantMixin is often imported after this registry
        try:
            from eden.tenancy.mixins import TenantMixin
            if issubclass(model_cls, TenantMixin):
                return True
        except ImportError:
            # If not yet available, we rely on the registry or explicit tags
            pass
            
        return False

    def enable_strict_mode(self, enabled: bool = True) -> None:
        """
        When strict mode is enabled, querying an isolated model without 
        a tenant context will raise a TenancyIsolationError instead 
        of returning an empty result.
        """
        self._strict_mode = enabled

    @property
    def strict_mode(self) -> bool:
        return self._strict_mode

def tenant_isolated(enabled: bool = True):
    """
    Decorator to mark a model class as tenant-isolated (or not).
    
    This is an alternative to setting `__tenant_isolated__ = True/False` 
    directly on the class.
    
    Example:
        @tenant_isolated(enabled=False)
        class GlobalReport(Model):
            ...
    """
    def decorator(model_cls: Type[Any]):
        setattr(model_cls, "__tenant_isolated__", enabled)
        # If enabled, ensure it's in the registry
        if enabled:
            tenancy_registry.register(model_cls)
        return model_cls
    return decorator

# Global singleton
tenancy_registry = TenancyRegistry()
