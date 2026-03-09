"""
Eden — Database Pagination

Provides a generic Page class and helpers for offset/limit pagination.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, computed_field

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    """
    A paginated result set containing the items and metadata
    about the current page and total available pages.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    items: Sequence[T]
    total: int
    page: int
    per_page: int

    @computed_field
    @property
    def total_pages(self) -> int:
        """Total number of pages based on total items and per_page limit."""
        if self.per_page == 0 or self.total == 0:
            return 0
        return math.ceil(self.total / self.per_page)

    @computed_field
    @property
    def has_next(self) -> bool:
        """True if there is a page after the current one."""
        return self.page < self.total_pages

    @computed_field
    @property
    def has_prev(self) -> bool:
        """True if there is a page before the current one."""
        return self.page > 1
