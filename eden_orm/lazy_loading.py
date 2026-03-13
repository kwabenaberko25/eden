"""
Lazy Loading - Load related objects on demand instead of eagerly

Allows objects to be fetched automatically when accessed through foreign key relationships:
- Access related object via attribute → automatically fetches from DB
- Caches result to avoid repeated queries
- Works with both single relationships (ForeignKey) and reverse relationships

Usage (Compatible with standard ORM patterns):
    user = await User.get(id=1)
    # Lazy load author on demand - use async context to trigger fetch
    # Store reference locally, then use in async context
"""

from typing import Any, Optional, Dict
from functools import wraps
import logging

logger = logging.getLogger(__name__)


# Note: The lazy loading module is now primarily for documentation.
# The actual lazy loading functionality is integrated into relationships.py
# and field_selection.py. This module is kept for backward compatibility.


class LazyPropertyCompat:
    """Compatibility layer for lazy loading via relationships.py descriptors."""
    
    def __init__(self, field_name: str, related_model_class: Any):
        """Initialize lazy load descriptor."""
        self.field_name = field_name
        self.related_model_class = related_model_class
        self.cache_attr = f"_lazycache_{field_name}"
    
    def __get__(self, instance, owner):
        """Called when accessing the attribute - return cached or None."""
        if instance is None:
            return self
        
        # Return cached value if available
        if hasattr(instance, self.cache_attr):
            return getattr(instance, self.cache_attr)
        
        # Return None if not loaded - lazy loading happens via select_related/prefetch_related
        return None
    
    def __set__(self, instance, value):
        """Allow setting the value."""
        setattr(instance, self.cache_attr, value)


# DEPRECATED: All lazy loading functionality has been moved to relationships.py
# This module is kept for backward compatibility only.
# Use relationships.py descriptors or prefetch_related/select_related on QuerySet instead.

__all__ = ['LazyPropertyCompat']

