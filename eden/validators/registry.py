from __future__ import annotations
"""Registry for validators."""


from typing import Any, Callable


class ValidatorRegistry:
    """Registry for managing validators globally."""

    _validators: dict[str, Callable[..., Any]] = {}

    @classmethod
    def register(cls, name: str, validator: Callable[..., Any]) -> None:
        """Register a validator."""
        cls._validators[name] = validator

    @classmethod
    def get(cls, name: str) -> Callable[..., Any] | None:
        """Get a registered validator."""
        return cls._validators.get(name)

    @classmethod
    def all(cls) -> dict[str, Callable[..., Any]]:
        """Get all registered validators."""
        return cls._validators.copy()

    @classmethod
    def clear(cls) -> None:
        """Clear all registered validators."""
        cls._validators.clear()
