"""
Eden — Role Hierarchy and RBAC System with Permission Registry

This module exports legacy RBAC components from eden.auth.access and introduces
the new PermissionRegistry for declarative, local policy enforcement.
"""

from typing import Any, Callable, Dict, Optional, Protocol

from eden.auth.access import RoleHierarchy as EdenRBAC, default_rbac

class PermissionPolicy(Protocol):
    async def __call__(self, user: Any, resource: Optional[Any] = None) -> bool:
        ...

class PermissionRegistry:
    """
    Decouples permission checks from hardcoded DB/external provider calls.
    Allows registering local policies for fast, synchronous, or custom logic checks.
    """
    def __init__(self) -> None:
        self._policies: Dict[str, PermissionPolicy] = {}

    def register(self, permission: str, policy: PermissionPolicy) -> None:
        """Register a policy function for a specific permission code."""
        self._policies[permission] = policy

    async def evaluate(self, permission: str, user: Any, resource: Optional[Any] = None) -> Optional[bool]:
        """
        Evaluate a registered policy.
        Returns True/False if a policy exists and makes a decision.
        Returns None if no matching local policy is registered.
        """
        policy = self._policies.get(permission)
        if policy:
            return await policy(user, resource)
        return None

# Global default instance
default_registry = PermissionRegistry()

__all__ = ["EdenRBAC", "default_rbac", "PermissionRegistry", "default_registry", "PermissionPolicy"]
