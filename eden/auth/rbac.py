"""
Eden — Role Hierarchy and RBAC System
"""

from typing import Dict, Set

class EdenRBAC:
    """
    Role-Based Access Control system supporting hierarchical roles.
    """
    def __init__(self):
        # Maps a role to its direct children (roles that inherit from it)
        # e.g., 'admin' -> ['manager'] means manager inherits from admin? No, usually it's:
        # parent = 'manager', children = 'admin' if admin has manager's permissions.
        # Let's map a role to its parents (roles it inherits FROM).
        # e.g., admin inherits from manager.
        self._hierarchy: Dict[str, Set[str]] = {}
        # Maps a role to its direct permissions
        self._permissions: Dict[str, Set[str]] = {}

    def add_role(self, role: str, parents: list[str] | None = None) -> None:
        """Register a new role and its parents (roles it inherits permissions from)."""
        if role not in self._hierarchy:
            self._hierarchy[role] = set()
        
        if parents:
            for parent in parents:
                self._hierarchy[role].add(parent)
                
    def add_permission(self, role: str, permission: str) -> None:
        """Grant a specific permission to a role."""
        if role not in self._permissions:
            self._permissions[role] = set()
        self._permissions[role].add(permission)

    def get_all_parents(self, role: str) -> Set[str]:
        """Recursively get all roles that this role inherits from."""
        parents = set()
        to_check = [role]
        
        while to_check:
            current = to_check.pop()
            direct_parents = self._hierarchy.get(current, set())
            for parent in direct_parents:
                if parent not in parents:
                    parents.add(parent)
                    to_check.append(parent)
                    
        return parents

    def get_all_permissions(self, role: str) -> Set[str]:
        """Get all permissions for a role, including inherited ones."""
        permissions = set(self._permissions.get(role, set()))
        
        for parent in self.get_all_parents(role):
            permissions.update(self._permissions.get(parent, set()))
            
        return permissions

    def has_permission(self, user_roles: list[str], permission: str) -> bool:
        """Check if any of the given roles grant the specific permission."""
        for role in user_roles:
            if permission in self.get_all_permissions(role):
                return True
        return False

# Global instance for typical simple usage
default_rbac = EdenRBAC()
