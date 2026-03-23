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
        name = model_cls.__name__
        if name not in self._isolated_models:
            logger.debug(f"Registering {name} as a tenant-isolated model.")
            self._isolated_models.add(name)

    def is_isolated(self, model_cls: Any) -> bool:
        """Check if a model class is registered for isolation."""
        # Check by name or instance of TenantMixin
        if model_cls.__name__ in self._isolated_models:
            return True
        
        # Fallback: check if it inherits from TenantMixin (if imported)
        # Note: TenantMixin is often imported after this registry
        from eden.tenancy.mixins import TenantMixin
        if issubclass(model_cls, TenantMixin):
            return True
            
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

# Global singleton
tenancy_registry = TenancyRegistry()
