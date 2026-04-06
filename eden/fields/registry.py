from __future__ import annotations


class FieldRegistry:
    """Registry for field types."""

    _registry: dict[str, type] = {}

    @classmethod
    def register(cls, name: str, field_class: type) -> None:
        cls._registry[name] = field_class

    @classmethod
    def get(cls, name: str) -> type | None:
        return cls._registry.get(name)

    @classmethod
    def all(cls) -> dict[str, type]:
        return cls._registry.copy()
