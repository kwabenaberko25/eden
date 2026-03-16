"""
Eden — Database Pagination

Provides a generic Page class and helpers for offset/limit pagination.
Supports automatic pagination link generation for REST APIs.

Usage:
    users = await User.select().paginate(page=1, per_page=10)
    # users.links contains: {"self": "/users?page=1&per_page=10", "next": "/users?page=2&...", ...}
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Generic, TypeVar, Optional, Dict, Any
from urllib.parse import urlencode

from pydantic import BaseModel, ConfigDict, computed_field

T = TypeVar("T")


class PaginationLinks(BaseModel):
    """Links for pagination navigation (HATEOAS)."""
    
    self: str
    first: Optional[str] = None
    last: Optional[str] = None
    next: Optional[str] = None
    prev: Optional[str] = None


class Page(BaseModel, Generic[T]):
    """
    A paginated result set containing the items and metadata
    about the current page and total available pages.
    
    Features:
    - Automatic pagination metadata (total, total_pages, has_next, has_prev)
    - HATEOAS links for pagination navigation
    - Customizable link generation
    
    Example:
        users = await User.select().paginate(page=1, per_page=10)
        
        print(users.total)       # Total items across all pages
        print(users.page)        # Current page number
        print(users.total_pages) # Total number of pages
        print(users.has_next)    # Is there a next page?
        print(users.links.next)  # URL for next page
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    items: Sequence[T]
    total: int
    page: int
    per_page: int
    links: Optional[PaginationLinks] = None

    @computed_field
    @property
    def total_pages(self) -> int:
        """Total number of pages based on total items and per_page limit."""
        if self.per_page == 0 or self.total == 0:
            return 0
        return math.ceil(self.total / self.per_page)

    @computed_field
    @property
    def pages(self) -> int:
        """Alias for total_pages for Django compatibility."""
        return self.total_pages

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
    
    @computed_field
    @property
    def offset(self) -> int:
        """Offset for this page in the result set."""
        return (self.page - 1) * self.per_page
    
    def generate_links(self, base_url: str, query_params: Optional[Dict[str, Any]] = None) -> PaginationLinks:
        """
        Generate HATEOAS pagination links.
        
        Args:
            base_url: Base URL without query string (e.g., "/api/users")
            query_params: Additional query parameters to include
        
        Returns:
            PaginationLinks with self, first, last, next, prev URLs
        
        Example:
            page = await User.select().paginate(page=2, per_page=10)
            links = page.generate_links("/api/users", {"filter": "active"})
            
            # Results in:
            # {
            #   "self": "/api/users?page=2&per_page=10&filter=active",
            #   "first": "/api/users?page=1&per_page=10&filter=active",
            #   "last": "/api/users?page=5&per_page=10&filter=active",
            #   "next": "/api/users?page=3&per_page=10&filter=active",
            #   "prev": "/api/users?page=1&per_page=10&filter=active",
            # }
        """
        params = query_params or {}
        params["per_page"] = self.per_page
        
        def build_url(page_num: int) -> str:
            """Build URL for page number."""
            page_params = {**params, "page": page_num}
            query_string = urlencode(page_params)
            return f"{base_url}?{query_string}"
        
        links = PaginationLinks(
            self=build_url(self.page),
            first=build_url(1),
            last=build_url(self.total_pages) if self.total_pages > 0 else None,
            next=build_url(self.page + 1) if self.has_next else None,
            prev=build_url(self.page - 1) if self.has_prev else None,
        )
        
        return links
