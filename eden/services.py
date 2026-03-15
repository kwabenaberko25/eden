"""
Eden — Business Logic Services
"""

from __future__ import annotations

from typing import Any, TypeVar, Generic

T = TypeVar("T")

class Service:
    """
    Base class for business logic services.
    
    Services are used to encapsulate domain logic, keeping
    models focused on data and views focused on presentation.
    
    Usage:
        class UserService(Service):
            async def register_user(self, data: dict):
                # ... logic ...
                pass
    """
    def __init__(self, **kwargs: Any) -> None:
        for key, value in kwargs.items():
            setattr(self, key, value)
