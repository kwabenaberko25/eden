"""
Eden — Authentication Models
"""

import uuid
from typing import Any, List, Optional
from sqlalchemy import JSON, Integer, Table, Column, ForeignKey, String, Uuid
from sqlalchemy.orm import mapped_column, Mapped, declared_attr, relationship, selectinload

from eden.auth.hashers import check_password, hash_password
from eden.auth.base import BaseUser as AuthBaseUser
from eden.db import Model, f, Relationship, Reference


# ── Association Tables ────────────────────────────────────────────────

# User <-> Role Many-to-Many
user_roles = Table(
    "eden_user_roles",
    Model.metadata,
    Column("user_id", Uuid, ForeignKey("eden_users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", Uuid, ForeignKey("eden_roles.id", ondelete="CASCADE"), primary_key=True),
)

# Role <-> Permission Many-to-Many
role_permissions = Table(
    "eden_role_permissions",
    Model.metadata,
    Column("role_id", Uuid, ForeignKey("eden_roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", Uuid, ForeignKey("eden_permissions.id", ondelete="CASCADE"), primary_key=True),
)

# Role <-> Role Many-to-Many (Hierarchy: Child -> Parent)
role_hierarchy = Table(
    "eden_role_hierarchy",
    Model.metadata,
    Column("child_role_id", Uuid, ForeignKey("eden_roles.id", ondelete="CASCADE"), primary_key=True),
    Column("parent_role_id", Uuid, ForeignKey("eden_roles.id", ondelete="CASCADE"), primary_key=True),
)


# ── RBAC Models ───────────────────────────────────────────────────────

class Permission(Model):
    """
    Granular access rights (e.g., 'users:write', 'billing:view').
    """
    __tablename__ = "eden_permissions"

    name: Mapped[str] = f(max_length=100, unique=True, index=True, label="Permission Key")
    description: Mapped[str | None] = f(nullable=True, label="Description")

    def __repr__(self) -> str:
        return f"<Permission(name='{self.name}')>"


class Role(Model):
    """
    Groups of permissions that can be assigned to users.
    Supports hierarchy (roles can inherit permissions from other roles).
    """
    __tablename__ = "eden_roles"

    name: Mapped[str] = f(max_length=100, unique=True, index=True, label="Role Name")
    description: Mapped[str | None] = f(nullable=True, label="Description")

    # Relationships
    permissions: Mapped[List[Permission]] = relationship(
        Permission, secondary=role_permissions, lazy="selectin"
    )

    # Hierarchical Support: A role can have multiple parent roles it inherits from
    parents: Mapped[List["Role"]] = relationship(
        "Role",
        secondary=role_hierarchy,
        primaryjoin=lambda: Role.id == role_hierarchy.c.child_role_id,
        secondaryjoin=lambda: Role.id == role_hierarchy.c.parent_role_id,
        backref="children",
        lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Role(name='{self.name}')>"

    async def get_all_permissions(self, visited: set[uuid.UUID] | None = None) -> set[str]:
        """
        Recursively resolve all permissions from this role and its parents.
        """
        if visited is None:
            visited = set()
        
        if self.id in visited:
            return set()
        
        visited.add(self.id)
        
        perms = {p.name for p in self.permissions}
        for parent in self.parents:
            perms.update(await parent.get_all_permissions(visited))
            
        return perms


# ── User Integration ──────────────────────────────────────────────────

class BaseUser(AuthBaseUser):
    """
    Mixin for User models.
    Provides common fields and methods for authentication and RBAC.
    """
    __allow_unmapped__ = True
    email: Mapped[str] = f(unique=True, index=True)
    password_hash: Mapped[str] = f()
    full_name: Mapped[str | None] = f(nullable=True)

    is_active: Mapped[bool] = f(default=True)
    is_staff: Mapped[bool] = f(default=False)
    is_superuser: Mapped[bool] = f(default=False)

    last_login: Mapped[str | None] = f(nullable=True)

    # Legacy role/permission storage (JSON overrides)
    roles_json: Mapped[list[str]] = mapped_column("roles", JSON, default=list)
    permissions_json: Mapped[list[str]] = mapped_column("permissions", JSON, default=list)

    # 1.0.0 Managed RBAC
    @declared_attr
    def roles(self) -> Mapped[List[Role]]:
        return relationship(Role, secondary=user_roles, lazy="selectin")

    # Track linked social accounts for multi-provider login
    @declared_attr
    def social_accounts(self) -> Mapped[list["SocialAccount"]]:
        return relationship("SocialAccount", back_populates="user", cascade="all, delete-orphan", overlaps="social_account")

    def set_password(self, password: str) -> None:
        """Hash and set the user's password."""
        self.password_hash = hash_password(password)

    def check_password(self, password: str) -> bool:
        """Verify a password against the stored hash."""
        return check_password(password, self.password_hash)

    async def get_roles(self) -> list[str]:
        """Get names of all roles assigned to this user (direct and via objects)."""
        names = set(self.roles_json or [])
        for role in self.roles:
            names.add(role.name)
        return list(names)

    async def get_all_role_names(self, visited: set[uuid.UUID] | None = None) -> set[str]:
        """Recursively resolve all role names in the hierarchy."""
        names = set(self.roles_json or [])
        
        if visited is None:
            visited = set()
            
        for role in self.roles:
            names.add(role.name)
            names.update(await self._get_parent_role_names(role, visited))
            
        return names

    async def _get_parent_role_names(self, role: Role, visited: set[uuid.UUID]) -> set[str]:
        """Internal helper for recursive role name resolution."""
        if role.id in visited:
            return set()
        visited.add(role.id)
        
        names = {role.name}
        for parent in role.parents:
            names.update(await self._get_parent_role_names(parent, visited))
        return names

    async def get_all_permissions(self) -> set[str]:
        """Resolve all permissions from JSON overrides and role hierarchy."""
        perms = set(self.permissions_json or [])
        
        # Resolve from relational roles
        visited_roles = set()
        for role in self.roles:
            perms.update(await role.get_all_permissions(visited_roles))
            
        return perms

    async def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission."""
        if getattr(self, "is_superuser", False):
            return True
        
        # Check explicit overrides first
        if permission in (self.permissions_json or []):
            return True
            
        # Check roles hierarchy
        all_perms = await self.get_all_permissions()
        return permission in all_perms

    async def has_role(self, role: str) -> bool:
        """Check if user belongs to a specific role."""
        if getattr(self, "is_superuser", False):
            return True
        
        # Check JSON roles
        if role in (self.roles_json or []):
            return True
            
        # Check relational roles
        for r in self.roles:
            if r.name == role:
                return True
        return False

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(email='{self.email}')>"


from eden.payments import CustomerMixin

class User(Model, BaseUser, CustomerMixin):
    """
    Main User model for the application.
    Linked to the 'eden_users' table.
    """
    __allow_unmapped__ = True
    __tablename__ = "eden_users"


class SocialAccount(Model):
    """
    Stores linked OAuth accounts (Google, GitHub, etc.) for a User.
    Allows a single user to have multiple login methods.
    """
    __tablename__ = "eden_social_accounts"

    provider: Mapped[str] = f(max_length=50)  # e.g., "google", "github"
    provider_user_id: Mapped[str] = f(max_length=255, index=True) # ID from the provider
    provider_metadata: Mapped[dict] = f(json=True, nullable=True)


    # Relationships (One-liner)
    user: Mapped["User"] = Reference(User, back_populates="social_accounts", overlaps="social_accounts")

    def __repr__(self) -> str:
        return f"<SocialAccount(provider='{self.provider}', user_id={self.user_id})>"
