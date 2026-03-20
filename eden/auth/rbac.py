"""
Eden — Role Hierarchy and RBAC System (Legacy Wrapper)

This module is now a legacy wrapper that exports components from eden.auth.access.
"""

from eden.auth.access import RoleHierarchy as EdenRBAC, default_rbac

__all__ = ["EdenRBAC", "default_rbac"]
