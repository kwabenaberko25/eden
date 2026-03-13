"""
Eden ORM - Pagination

Pagination utilities for query results.
"""

from typing import List, Any, Generic, TypeVar
from dataclasses import dataclass
import math

T = TypeVar("T")


@dataclass
class Page(Generic[T]):
    """Represents a page of results."""
    
    items: List[T]
    page: int
    per_page: int
    total: int
    
    @property
    def total_pages(self) -> int:
        """Total number of pages."""
        return math.ceil(self.total / self.per_page)
    
    @property
    def has_previous(self) -> bool:
        """Check if there's a previous page."""
        return self.page > 1
    
    @property
    def has_next(self) -> bool:
        """Check if there's a next page."""
        return self.page < self.total_pages
    
    @property
    def previous_page(self) -> int:
        """Previous page number."""
        return self.page - 1
    
    @property
    def next_page(self) -> int:
        """Next page number."""
        return self.page + 1
    
    @property
    def start_index(self) -> int:
        """Index of first item (0-based)."""
        return (self.page - 1) * self.per_page
    
    @property
    def end_index(self) -> int:
        """Index of last item (0-based, inclusive)."""
        return min(self.page * self.per_page - 1, self.total - 1)
