from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict

class SerializationMixin:
    """
    Mixin that provides serialization methods for Eden models.
    """

    def model_dump(self, **kwargs) -> Dict[str, Any]:
        """Manual implementation of model serialization."""
        exclude = kwargs.get("exclude", set())
        include = kwargs.get("include", None)

        data = {}
        # Get columns from the table
        for column in self.__table__.columns:
            name = column.name
            if name in exclude:
                continue
            if include is not None and name not in include:
                continue

            value = getattr(self, name)
            if isinstance(value, uuid.UUID):
                value = str(value)
            elif isinstance(value, datetime):
                value = value.isoformat()
            data[name] = value
        return data

    def to_dict(self, **kwargs) -> Dict[str, Any]:
        """Convert model instance to dictionary (utility)."""
        return self.model_dump(**kwargs)
