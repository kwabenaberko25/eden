"""
Eden Framework — Cursor-Based Pagination

Efficient keyset pagination for large datasets without offset calculations.

**Key Advantages:**
- No N+1 queries (uses WHERE > last_key instead of OFFSET)
- Consistent pagination even with insertions/deletions
- Bidirectional navigation (next/prev)
- Works with any sortable field(s)
- Supports both SQLAlchemy queries and plain Python lists

**Usage (list mode):**

    from eden.db.cursor import CursorPaginator
    
    items = [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}, ...]
    paginator = CursorPaginator(sort_field="id")
    
    # First page
    page = paginator.paginate(items, limit=20)
    print(page.next_cursor)
    
    # Next page
    page = paginator.paginate(items, after=page.next_cursor, limit=20)

**Usage (query mode):**

    paginator = CursorPaginator(User.query(), sort_by="id")
    
    page = await paginator.paginate(cursor=None, limit=20)
    print(page.next_cursor)
    
    page = await paginator.paginate(cursor=page.next_cursor, limit=20)
"""

import base64
import json
import logging
from typing import Any, Dict, List, Optional, Type, Generic, TypeVar, Union
from dataclasses import dataclass

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class CursorPage(Generic[T]):
    """Result of cursor pagination."""
    items: List[T]
    next_cursor: Optional[str] = None
    prev_cursor: Optional[str] = None
    has_next: bool = False
    has_prev: bool = False
    total_items: Optional[int] = None  # Not always available


class CursorToken:
    """Encodes/decodes cursor tokens for pagination."""
    
    @staticmethod
    def encode(sort_values: Dict[str, Any]) -> str:
        """
        Encode cursor from sort field values.
        
        Args:
            sort_values: Dict of field_name -> value
        
        Returns:
            Base64-encoded cursor token
        """
        json_str = json.dumps(sort_values, default=str)
        return base64.urlsafe_b64encode(json_str.encode()).decode()
    
    @staticmethod
    def decode(token: str) -> Optional[Dict[str, Any]]:
        """
        Decode cursor token.
        
        Args:
            token: Base64-encoded cursor token
        
        Returns:
            Dict of field_name -> value, or None if invalid
        """
        try:
            json_bytes = base64.urlsafe_b64decode(token.encode())
            return json.loads(json_bytes)
        except Exception as e:
            logger.warning(f"Failed to decode cursor token: {e}")
            return None


class CursorPaginator:
    """
    Keyset-based paginator for efficient pagination.
    
    Supports two modes:
    
    1. **List mode** (synchronous): Pass items directly to ``paginate()``.
       Constructor takes only ``sort_field``/``sort_by``.
    
    2. **Query mode** (asynchronous): Wraps a SQLAlchemy query object.
       Constructor takes ``query`` as the first positional arg.
    
    Examples:
        # List mode
        paginator = CursorPaginator(sort_field="id")
        page = paginator.paginate(items, limit=10)
        
        # Query mode
        paginator = CursorPaginator(User.query(), sort_by="id")
        page = await paginator.paginate_query(limit=10)
    """
    
    def __init__(
        self,
        query: Any = None,
        sort_by: Optional[Union[str, List[str]]] = None,
        sort_field: Optional[str] = None,
        ascending: bool = True,
    ):
        """
        Initialize cursor paginator.
        
        Args:
            query: SQLAlchemy query object (optional, for query mode)
            sort_by: Field(s) to sort by. Accepts str or list of str.
            sort_field: Alias for sort_by (accepts single field name).
            ascending: Sort order (default: ascending)
        """
        self.query = query
        
        # Resolve sort fields: sort_field (alias) takes priority if sort_by not given
        effective_sort = sort_by or sort_field or "id"
        self.sort_fields = [effective_sort] if isinstance(effective_sort, str) else effective_sort
        self.ascending = ascending
    
    # =========================================================================
    # List mode (synchronous)
    # =========================================================================
    
    def paginate(
        self,
        items: Optional[List[Any]] = None,
        cursor: Optional[str] = None,
        after: Optional[str] = None,
        before: Optional[str] = None,
        limit: int = 20,
        direction: str = "forward",
    ) -> CursorPage[Any]:
        """
        Paginate a list of items synchronously.
        
        Args:
            items: List of dicts or objects to paginate.
                   If None, falls back to the stored query (raises if also None).
            cursor: Pagination cursor (alias for ``after``).
            after: Cursor for forward pagination (after this position).
            before: Cursor for backward pagination (before this position).
            limit: Number of items per page.
            direction: "forward" or "backward" (auto-detected from after/before).
        
        Returns:
            CursorPage with items and navigation cursors.
        """
        if items is None:
            raise ValueError(
                "items is required for list-mode pagination. "
                "For query-mode, use paginate_query()."
            )
        
        # Resolve cursor from aliases
        effective_cursor = after or cursor
        if before is not None:
            effective_cursor = before
            direction = "backward"
        elif after is not None:
            direction = "forward"
        
        # Sort items
        sort_field = self.sort_fields[0]
        reverse = not self.ascending
        if direction == "backward":
            reverse = not reverse
        
        sorted_items = sorted(
            items,
            key=lambda x: self._get_field_value(x, sort_field),
            reverse=reverse,
        )
        
        # Apply cursor filter
        if effective_cursor:
            cursor_values = CursorToken.decode(effective_cursor)
            if cursor_values:
                cursor_val = cursor_values.get(sort_field)
                if cursor_val is not None:
                    if direction == "forward":
                        if self.ascending:
                            sorted_items = [
                                it for it in sorted_items
                                if self._get_field_value(it, sort_field) > cursor_val
                            ]
                        else:
                            sorted_items = [
                                it for it in sorted_items
                                if self._get_field_value(it, sort_field) < cursor_val
                            ]
                    else:  # backward
                        if self.ascending:
                            sorted_items = [
                                it for it in sorted_items
                                if self._get_field_value(it, sort_field) < cursor_val
                            ]
                        else:
                            sorted_items = [
                                it for it in sorted_items
                                if self._get_field_value(it, sort_field) > cursor_val
                            ]
        
        # Determine has_more
        has_more = len(sorted_items) > limit
        page_items = sorted_items[:limit]
        
        # Generate cursors
        next_cursor = None
        prev_cursor = None
        has_next = False
        has_prev = False
        
        if page_items:
            if has_more:
                last = page_items[-1]
                next_cursor = CursorToken.encode(
                    {sort_field: self._get_field_value(last, sort_field)}
                )
                has_next = True
            
            if effective_cursor:
                first = page_items[0]
                prev_cursor = CursorToken.encode(
                    {sort_field: self._get_field_value(first, sort_field)}
                )
                has_prev = True
        
        return CursorPage(
            items=page_items,
            next_cursor=next_cursor,
            prev_cursor=prev_cursor,
            has_next=has_next,
            has_prev=has_prev,
            total_items=len(items),
        )
    
    @staticmethod
    def _get_field_value(item: Any, field: str) -> Any:
        """Extract a field value from a dict or object."""
        if isinstance(item, dict):
            return item.get(field)
        return getattr(item, field, None)
    
    # =========================================================================
    # Query mode (asynchronous)
    # =========================================================================
    
    async def paginate_query(
        self,
        cursor: Optional[str] = None,
        limit: int = 20,
        direction: str = "forward",
    ) -> CursorPage[Any]:
        """
        Paginate using a SQLAlchemy query (asynchronous).
        
        Args:
            cursor: Pagination cursor (None for first page)
            limit: Number of items to fetch (+ 1 for has_next detection)
            direction: "forward" or "backward"
        
        Returns:
            CursorPage with items and cursors for next/prev
        """
        if self.query is None:
            raise ValueError("query is required for query-mode pagination.")
        
        if direction not in ("forward", "backward"):
            raise ValueError("direction must be 'forward' or 'backward'")
        
        # Decode cursor
        cursor_values = CursorToken.decode(cursor) if cursor else None
        
        # Build query
        query = self.query
        
        # Apply cursor filter
        if cursor_values:
            query = self._apply_cursor_filter(query, cursor_values, direction)
        
        # Apply sorting
        query = self._apply_sort(query, direction)
        
        # Fetch limit + 1 to detect has_next/has_prev
        items = await query.limit(limit + 1).all()
        
        # Determine if there are more items
        has_more = len(items) > limit
        if has_more:
            items = items[:limit]
        
        # Generate cursors
        if items:
            # Next cursor
            next_cursor = None
            if has_more:
                last_item = items[-1]
                sort_vals = self._extract_sort_values(last_item)
                next_cursor = CursorToken.encode(sort_vals)
            
            # Prev cursor (from first item)
            prev_cursor = None
            if cursor_values:  # We have a previous position
                first_item = items[0]
                sort_vals = self._extract_sort_values(first_item)
                prev_cursor = CursorToken.encode(sort_vals)
        else:
            next_cursor = None
            prev_cursor = None
        
        return CursorPage(
            items=items,
            next_cursor=next_cursor,
            prev_cursor=prev_cursor,
            has_next=has_more and direction == "forward",
            has_prev=has_more and direction == "backward",
        )
    
    def _apply_cursor_filter(
        self,
        query: Any,
        cursor_values: Dict[str, Any],
        direction: str,
    ) -> Any:
        """Apply cursor filter to query."""
        from eden.db import Q
        
        operator = ">" if direction == "forward" and self.ascending else "<"
        
        # Build filter condition for each sort field
        for field_name in self.sort_fields:
            if field_name in cursor_values:
                value = cursor_values[field_name]
                if operator == ">":
                    query = query.filter(**{f"{field_name}__gt": value})
                else:
                    query = query.filter(**{f"{field_name}__lt": value})
        
        return query
    
    def _apply_sort(self, query: Any, direction: str) -> Any:
        """Apply sorting to query."""
        sort_fields = []
        for field in self.sort_fields:
            if direction == "forward" and self.ascending:
                sort_fields.append(field)
            elif direction == "forward" and not self.ascending:
                sort_fields.append(f"-{field}")
            elif direction == "backward" and self.ascending:
                sort_fields.append(f"-{field}")
            else:
                sort_fields.append(field)
        
        return query.order_by(*sort_fields)
    
    def _extract_sort_values(self, item: Any) -> Dict[str, Any]:
        """Extract sort field values from an item."""
        values = {}
        for field_name in self.sort_fields:
            values[field_name] = getattr(item, field_name, None)
        return values


# Helper function for model integration
async def paginate(
    query: Any,
    cursor: Optional[str] = None,
    limit: int = 20,
    sort_by: str = "id",
) -> CursorPage[Any]:
    """
    Convenience function for cursor pagination (query mode).
    
    Usage:
        page = await paginate(User.query(), cursor=request.query_params.get("cursor"))
        for user in page.items:
            print(user.email)
    """
    paginator = CursorPaginator(query, sort_by=sort_by)
    return await paginator.paginate_query(cursor=cursor, limit=limit)
