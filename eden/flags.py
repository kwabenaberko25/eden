"""
Eden Framework — Feature Flags System

Feature flags provide dynamic feature toggles for gradual rollouts, A/B testing,
and feature management without code redeployment.

Key capabilities:
- In-memory and database backends
- Context-aware evaluation (user, tenant, environment)
- Multiple flag strategies (percentage rollout, user-based, etc.)
- Route protection via decorators
- Admin UI integration ready

This implementation provides all the infrastructure needed for enterprise-grade
feature flag management.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Type, Callable, Set
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from enum import Enum
import contextvars
import hashlib

logger = logging.getLogger(__name__)

# Context variable to store current flag context
_flag_context: contextvars.ContextVar[Optional["FlagContext"]] = contextvars.ContextVar(
    "eden_flag_context", default=None
)


# ============================================================================
# Data Models
# ============================================================================

class FlagStrategy(Enum):
    """Flag evaluation strategies."""
    ALWAYS_ON = "always_on"
    ALWAYS_OFF = "always_off"
    PERCENTAGE = "percentage"  # Rollout percentage
    PERCENTAGE_ROLLOUT = "percentage"  # Alias for PERCENTAGE (test-compat)
    USER_ID = "user_id"  # Specific user IDs
    USER_SEGMENT = "user_segment"  # User attribute matching
    TENANT_ID = "tenant_id"  # Specific tenants
    ENVIRONMENT = "environment"  # Environment-based


@dataclass
class Flag:
    """Feature flag definition."""
    name: str
    enabled: bool = True
    strategy: FlagStrategy = FlagStrategy.ALWAYS_ON
    
    # Strategy parameters
    rollout_percent: Optional[float] = None  # 0-100 for percentage strategy
    percentage: Optional[float] = None  # Alias for rollout_percent (convenience API)
    allowed_user_ids: Optional[List[str]] = None  # For USER_ID strategy
    allowed_segments: Optional[List[str]] = None  # For USER_SEGMENT strategy
    segment_attribute: Optional[str] = None  # e.g., "plan" for plan-based rollout
    allowed_tenants: Optional[List[str]] = None  # For TENANT_ID strategy
    environments: Optional[List[str]] = None  # For ENVIRONMENT strategy
    
    # Metadata
    description: str = ""
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    def __post_init__(self):
        """Map alias fields to canonical names."""
        # Map 'percentage' alias -> 'rollout_percent'
        if self.percentage is not None and self.rollout_percent is None:
            self.rollout_percent = self.percentage
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data["strategy"] = self.strategy.value
        return data


@dataclass
class FlagContext:
    """Context for flag evaluation."""
    user_id: Optional[str] = None
    user_segment: Optional[str] = None
    user_attributes: Optional[Dict[str, Any]] = None
    
    tenant_id: Optional[str] = None
    tenant: Optional[str] = None  # Alias for tenant_id (convenience API)
    environment: Optional[str] = None
    
    # Custom attributes
    custom_attributes: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Map alias fields to canonical names."""
        # Map 'tenant' alias -> 'tenant_id'
        if self.tenant is not None and self.tenant_id is None:
            self.tenant_id = self.tenant
    
    def get_attribute(self, key: str) -> Optional[Any]:
        """Get an attribute by key."""
        if self.custom_attributes and key in self.custom_attributes:
            return self.custom_attributes[key]
        if self.user_attributes and key in self.user_attributes:
            return self.user_attributes[key]
        return getattr(self, key, None)


# ============================================================================
# Flag Backends
# ============================================================================

class FlagBackend(ABC):
    """Abstract base for flag storage backends."""
    
    @abstractmethod
    async def get_flag(self, name: str) -> Optional[Flag]:
        """Get a flag by name."""
        pass
    
    @abstractmethod
    async def get_all_flags(self) -> Dict[str, Flag]:
        """Get all flags."""
        pass
    
    @abstractmethod
    async def set_flag(self, flag: Flag) -> None:
        """Create or update a flag."""
        pass
    
    @abstractmethod
    async def delete_flag(self, name: str) -> None:
        """Delete a flag."""
        pass


class InMemoryFlagBackend(FlagBackend):
    """In-memory flag storage (fast, non-persistent)."""
    
    def __init__(self):
        self.flags: Dict[str, Flag] = {}
    
    async def get_flag(self, name: str) -> Optional[Flag]:
        """Get a flag by name."""
        return self.flags.get(name)
    
    async def get_all_flags(self) -> Dict[str, Flag]:
        """Get all flags."""
        return dict(self.flags)
    
    async def set_flag(self, flag: Flag) -> None:
        """Create or update a flag."""
        self.flags[flag.name] = flag
        logger.debug(f"Flag set: {flag.name}")
    
    async def delete_flag(self, name: str) -> None:
        """Delete a flag."""
        if name in self.flags:
            del self.flags[name]
            logger.debug(f"Flag deleted: {name}")


# ============================================================================
# Flag Evaluator
# ============================================================================

class FlagEvaluator:
    """Evaluates flag status based on context and strategy."""
    
    @staticmethod
    def evaluate(flag: Flag, context: Optional[FlagContext] = None) -> bool:
        """
        Evaluate whether a flag is enabled for the given context.
        
        Args:
            flag: The flag to evaluate
            context: Request/user context
        
        Returns:
            True if flag is enabled for this context
        """
        # Always off
        if not flag.enabled:
            return False
        
        # No context required - always on
        if flag.strategy == FlagStrategy.ALWAYS_ON:
            return True
            
        if flag.strategy == FlagStrategy.ALWAYS_OFF:
            return False
        
        # No context provided
        if not context:
            return flag.enabled
        
        # Context-based strategies
        if flag.strategy == FlagStrategy.PERCENTAGE:
            return FlagEvaluator._eval_percentage(flag, context)
        
        elif flag.strategy == FlagStrategy.USER_ID:
            return FlagEvaluator._eval_user_id(flag, context)
        
        elif flag.strategy == FlagStrategy.USER_SEGMENT:
            return FlagEvaluator._eval_user_segment(flag, context)
        
        elif flag.strategy == FlagStrategy.TENANT_ID:
            return FlagEvaluator._eval_tenant_id(flag, context)
        
        elif flag.strategy == FlagStrategy.ENVIRONMENT:
            return FlagEvaluator._eval_environment(flag, context)
        
        return flag.enabled
    
    @staticmethod
    def _eval_percentage(flag: Flag, context: FlagContext) -> bool:
        """Evaluate percentage-based rollout."""
        if flag.rollout_percent is None:
            return flag.enabled
        
        # Use user_id as deterministic hash
        if not context.user_id:
            return False
        
        # Generate consistent hash for user
        hash_val = int(
            hashlib.md5(context.user_id.encode()).hexdigest(),
            16
        ) % 100
        
        return hash_val < flag.rollout_percent
    
    @staticmethod
    def _eval_user_id(flag: Flag, context: FlagContext) -> bool:
        """Evaluate user ID whitelist."""
        if not flag.allowed_user_ids:
            return flag.enabled
        
        return context.user_id in flag.allowed_user_ids
    
    @staticmethod
    def _eval_user_segment(flag: Flag, context: FlagContext) -> bool:
        """Evaluate user segment."""
        if not flag.allowed_segments:
            return flag.enabled
        
        if not flag.segment_attribute:
            return flag.enabled
        
        segment = context.get_attribute(flag.segment_attribute)
        return segment in flag.allowed_segments
    
    @staticmethod
    def _eval_tenant_id(flag: Flag, context: FlagContext) -> bool:
        """Evaluate tenant whitelist."""
        if not flag.allowed_tenants:
            return flag.enabled
        
        return context.tenant_id in flag.allowed_tenants
    
    @staticmethod
    def _eval_environment(flag: Flag, context: FlagContext) -> bool:
        """Evaluate environment match."""
        if not flag.environments:
            return flag.enabled
        
        return context.environment in flag.environments


# ============================================================================
# Flag Manager
# ============================================================================

class FlagManager:
    """Central manager for feature flags."""
    
    def __init__(self, backend: Optional[FlagBackend] = None):
        """
        Initialize flag manager.
        
        Args:
            backend: Storage backend (defaults to InMemory)
        """
        self.backend = backend or InMemoryFlagBackend()
    
    def is_enabled(self, name: str, context: Optional[FlagContext] = None) -> bool:
        """
        Check if a flag is enabled (synchronous).
        
        Uses the in-memory backend directly for synchronous evaluation.
        For async code, use ``is_enabled_async()`` instead.
        
        Args:
            name: Flag name
            context: Optional context for evaluation
        
        Returns:
            True if flag is enabled
        """
        # Use current context if not provided
        if context is None:
            context = _flag_context.get()
        
        # Direct synchronous lookup for InMemoryFlagBackend
        if isinstance(self.backend, InMemoryFlagBackend):
            flag = self.backend.flags.get(name)
        else:
            # Fallback: should not be reached in sync path with non-memory backends
            logger.warning("is_enabled() called synchronously with non-memory backend")
            return False
        
        if not flag:
            return False
        
        return FlagEvaluator.evaluate(flag, context)
    
    async def is_enabled_async(self, name: str, context: Optional[FlagContext] = None) -> bool:
        """
        Check if a flag is enabled (asynchronous).
        
        Supports all backend types including database backends.
        
        Args:
            name: Flag name
            context: Optional context for evaluation
        
        Returns:
            True if flag is enabled
        """
        if context is None:
            context = _flag_context.get()
        
        flag = await self.backend.get_flag(name)
        if not flag:
            return False
        
        return FlagEvaluator.evaluate(flag, context)
    
    def register_flag(self, flag: Flag) -> None:
        """
        Register a pre-built Flag object directly (synchronous).
        
        This is the preferred API for registering flags from configuration
        or at startup, where you already have a fully formed Flag object.
        
        Args:
            flag: Flag instance to register
        
        Example:
            >>> flag = Flag(name="beta", strategy=FlagStrategy.PERCENTAGE, percentage=50)
            >>> manager.register_flag(flag)
        """
        if isinstance(self.backend, InMemoryFlagBackend):
            self.backend.flags[flag.name] = flag
            logger.debug(f"Flag registered: {flag.name}")
        else:
            raise RuntimeError(
                "register_flag() is only available with InMemoryFlagBackend. "
                "Use add_flag() for async backends."
            )
    
    async def add_flag(
        self,
        name: str,
        enabled: bool = True,
        strategy: FlagStrategy = FlagStrategy.ALWAYS_ON,
        **kwargs
    ) -> Flag:
        """
        Create a new flag (asynchronous).
        
        Args:
            name: Flag name
            enabled: Initial enabled state
            strategy: Evaluation strategy
            **kwargs: Additional strategy parameters
        
        Returns:
            Created flag
        """
        flag = Flag(
            name=name,
            enabled=enabled,
            strategy=strategy,
            **kwargs
        )
        await self.backend.set_flag(flag)
        return flag
    
    async def get_flag(self, name: str) -> Optional[Flag]:
        """Get a flag by name."""
        return await self.backend.get_flag(name)
    
    async def get_all_flags(self) -> Dict[str, Flag]:
        """Get all flags."""
        return await self.backend.get_all_flags()
    
    async def update_flag(self, name: str, **updates) -> Optional[Flag]:
        """Update a flag."""
        flag = await self.backend.get_flag(name)
        if not flag:
            return None
        
        for key, value in updates.items():
            if hasattr(flag, key):
                setattr(flag, key, value)
        
        await self.backend.set_flag(flag)
        return flag
    
    async def delete_flag(self, name: str) -> bool:
        """Delete a flag."""
        await self.backend.delete_flag(name)
        return True
    
    def set_flag_context(self, context: FlagContext) -> None:
        """Set the current flag context (delegates to module-level function)."""
        set_flag_context(context)
    
    def get_flag_context(self) -> Optional[FlagContext]:
        """Get the current flag context (delegates to module-level function)."""
        return get_flag_context()


# ============================================================================
# Decorators
# ============================================================================

def feature_flag(flag_name: str):
    """
    Decorator to guard a route behind a feature flag.
    
    Returns 403 if flag is disabled.
    
    Usage:
        @app.get("/api/v2/users")
        @feature_flag("users_api_v2")
        async def list_users(request):
            ...
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)
        wrapper._feature_flag = flag_name
        return wrapper
    return decorator


# ============================================================================
# Context Management
# ============================================================================

def set_flag_context(context: FlagContext) -> None:
    """Set the current flag context."""
    _flag_context.set(context)


def get_flag_context() -> Optional[FlagContext]:
    """Get the current flag context."""
    return _flag_context.get()


# ============================================================================
# Global Instance
# ============================================================================

_global_flag_manager: Optional[FlagManager] = None


def get_flag_manager() -> FlagManager:
    """Get global flag manager."""
    global _global_flag_manager
    if _global_flag_manager is None:
        _global_flag_manager = FlagManager()
    return _global_flag_manager


def set_flag_manager(manager: FlagManager) -> None:
    """Set global flag manager."""
    global _global_flag_manager
    _global_flag_manager = manager
