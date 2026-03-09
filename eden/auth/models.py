"""
Eden — Authentication Models
"""


from typing import Any
from sqlalchemy import JSON, Integer
from sqlalchemy.orm import mapped_column, Mapped, declared_attr

from eden.auth.hashers import check_password, hash_password
from eden.db import Model, f, Relationship, Reference


class BaseUser:
    """
    Mixin for User models.
    Provides common fields and methods for authentication.
    """
    __allow_unmapped__ = True
    email: Mapped[str] = f(unique=True, index=True)
    password_hash: Mapped[str] = f()
    full_name: Mapped[str | None] = f(nullable=True)

    is_active: Mapped[bool] = f(default=True)
    is_staff: Mapped[bool] = f(default=False)
    is_superuser: Mapped[bool] = f(default=False)

    last_login: Mapped[str | None] = f(nullable=True)

    # Internal role/permission storage
    # Developers can override this or use a separate table
    roles: Mapped[list[str]] = mapped_column(JSON, default=list)
    permissions: Mapped[list[str]] = mapped_column(JSON, default=list)

    # Track linked social accounts for multi-provider login
    @declared_attr
    def social_accounts(self) -> Mapped[list["SocialAccount"]]:
        return Relationship("SocialAccount", back_populates="user", cascade="all, delete-orphan")

    def set_password(self, password: str) -> None:
        """Hash and set the user's password."""
        self.password_hash = hash_password(password)

    def check_password(self, password: str) -> bool:
        """Verify a password against the stored hash."""
        return check_password(password, self.password_hash)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(email='{self.email}')>"

class User(Model, BaseUser):
    """
    Main User model for the application.
    Linked to the 'eden_users' table.
    """
    __allow_unmapped__ = True
    __tablename__ = "eden_users"
    id: Mapped[int] = f(primary_key=True)

class SocialAccount(Model):
    """
    Stores linked OAuth accounts (Google, GitHub, etc.) for a User.
    Allows a single user to have multiple login methods.
    """
    __tablename__ = "eden_social_accounts"

    id: Mapped[int] = f(primary_key=True)
    provider: str = f(max_length=50)  # e.g., "google", "github"
    provider_user_id: str = f(max_length=255, index=True) # ID from the provider
    provider_metadata: dict = f(json=True, nullable=True)

    # Relationships (One-liner)
    user: Mapped["User"] = Reference(back_populates="social_accounts", fk_type=Integer, overlaps="social_accounts")

    def __repr__(self) -> str:
        return f"<SocialAccount(provider='{self.provider}', user_id={self.user_id})>"
