"""
Eden Template Caching System

Optimizes template rendering through intelligent caching:
  - Compiled code caching (AST → Python bytecode)
  - Template metadata caching
  - Inheritance chain caching
  - Smart cache invalidation

Design:
  - TemplateCache: Main caching interface
  - CompilationCache: Caches compiled code
  - InheritanceCache: Caches resolved inheritance chains
  - CacheKey: Unique cache identifiers
  - CacheStrategy: Cache eviction policies
"""

import hashlib
import asyncio
import time
from typing import Dict, Optional, Any, Callable, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
from collections import OrderedDict


class CacheStrategy(Enum):
    """Cache eviction strategies."""
    LRU = "least_recently_used"  # Least recently used
    LFU = "least_frequently_used"  # Least frequently used
    FIFO = "first_in_first_out"  # First in first out
    TTL = "time_to_live"  # Time-based expiration
    NONE = "none"  # No eviction


@dataclass
class CacheEntry:
    """Single cache entry with metadata."""
    
    key: str
    value: Any
    created_at: float = field(default_factory=time.time)
    accessed_at: float = field(default_factory=time.time)
    access_count: int = 1
    ttl: Optional[float] = None  # Time to live in seconds
    
    def is_expired(self) -> bool:
        """Check if entry has expired."""
        if self.ttl is None:
            return False
        elapsed = time.time() - self.created_at
        return elapsed > self.ttl
    
    def touch(self) -> None:
        """Update access time and count."""
        self.accessed_at = time.time()
        self.access_count += 1


@dataclass
class CacheStats:
    """Cache performance statistics."""
    
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    size: int = 0
    max_size: int = 0
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return self.hits / total
    
    def __repr__(self) -> str:
        hit_pct = self.hit_rate * 100
        return (f"CacheStats(hits={self.hits}, misses={self.misses}, "
                f"hit_rate={hit_pct:.1f}%, size={self.size}, evictions={self.evictions})")


class CacheKey:
    """
    Unique cache key generation for templates.
    
    Combines template name, content hash, and context to generate stable keys.
    """
    
    @staticmethod
    def for_compilation(template_name: str, template_content: str) -> str:
        """Generate cache key for compiled template."""
        content_hash = hashlib.sha256(template_content.encode()).hexdigest()[:8]
        return f"compile:{template_name}:{content_hash}"
    
    @staticmethod
    def for_inheritance_chain(template_name: str, chain_templates: List[str]) -> str:
        """Generate cache key for inheritance chain."""
        chain_str = "|".join(chain_templates)
        chain_hash = hashlib.sha256(chain_str.encode()).hexdigest()[:8]
        return f"chain:{template_name}:{chain_hash}"
    
    @staticmethod
    def for_rendered(template_name: str, context_hash: str) -> str:
        """Generate cache key for rendered template."""
        return f"render:{template_name}:{context_hash}"
    
    @staticmethod
    def context_hash(context: Dict[str, Any]) -> str:
        """Generate hash of context variables."""
        import json
        try:
            context_str = json.dumps(context, sort_keys=True, default=str)
            return hashlib.sha256(context_str.encode()).hexdigest()[:8]
        except (TypeError, ValueError):
            return "unstable"


class BaseCache(ABC):
    """Abstract base for all cache implementations."""
    
    def __init__(self, max_size: int = 1000, strategy: CacheStrategy = CacheStrategy.LRU):
        self.max_size = max_size
        self.strategy = strategy
        self.entries: OrderedDict[str, CacheEntry] = OrderedDict()
        self.stats = CacheStats(max_size=max_size)
    
    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """Set value in cache."""
        pass
    
    def has(self, key: str) -> bool:
        """Check if key exists in cache."""
        return key in self.entries
    
    def delete(self, key: str) -> None:
        """Delete entry from cache."""
        if key in self.entries:
            del self.entries[key]
    
    def clear(self) -> None:
        """Clear entire cache."""
        self.entries.clear()
        self.stats = CacheStats(max_size=self.max_size)
    
    def size(self) -> int:
        """Get current cache size."""
        return len(self.entries)
    
    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        self.stats.size = len(self.entries)
        return self.stats


class LRUCache(BaseCache):
    """Least Recently Used cache implementation."""
    
    def get(self, key: str) -> Optional[Any]:
        """Get value and mark as recently used."""
        if key not in self.entries:
            self.stats.misses += 1
            return None
        
        entry = self.entries[key]
        
        if entry.is_expired():
            del self.entries[key]
            self.stats.misses += 1
            return None
        
        entry.touch()
        # Move to end (most recently used)
        self.entries.move_to_end(key)
        self.stats.hits += 1
        return entry.value
    
    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """Set value in cache, evicting LRU if needed."""
        # If key exists, update it
        if key in self.entries:
            self.entries[key].value = value
            self.entries[key].ttl = ttl
            self.entries.move_to_end(key)
            return
        
        # Create new entry
        self.entries[key] = CacheEntry(key, value, ttl=ttl)
        
        # Evict LRU if over capacity
        while len(self.entries) > self.max_size:
            lru_key, _ = self.entries.popitem(last=False)
            self.stats.evictions += 1


class LFUCache(BaseCache):
    """Least Frequently Used cache implementation."""
    
    def get(self, key: str) -> Optional[Any]:
        """Get value and increase frequency."""
        if key not in self.entries:
            self.stats.misses += 1
            return None
        
        entry = self.entries[key]
        
        if entry.is_expired():
            del self.entries[key]
            self.stats.misses += 1
            return None
        
        entry.touch()
        self.stats.hits += 1
        return entry.value
    
    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """Set value in cache, evicting LFU if needed."""
        if key in self.entries:
            self.entries[key].value = value
            self.entries[key].ttl = ttl
            return
        
        self.entries[key] = CacheEntry(key, value, ttl=ttl)
        
        # Evict LFU if over capacity
        while len(self.entries) > self.max_size:
            # Find least frequently used
            lfu_key = min(
                (k for k in self.entries if k != key),
                key=lambda k: self.entries[k].access_count,
                default=None
            )
            if lfu_key:
                del self.entries[lfu_key]
                self.stats.evictions += 1


class TTLCache(BaseCache):
    """Time-To-Live cache implementation with expiration."""
    
    def __init__(self, max_size: int = 1000, default_ttl: float = 3600):
        super().__init__(max_size, CacheStrategy.TTL)
        self.default_ttl = default_ttl
    
    def get(self, key: str) -> Optional[Any]:
        """Get value if not expired."""
        if key not in self.entries:
            self.stats.misses += 1
            return None
        
        entry = self.entries[key]
        
        if entry.is_expired():
            del self.entries[key]
            self.stats.misses += 1
            return None
        
        entry.touch()
        self.stats.hits += 1
        return entry.value
    
    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """Set value with optional TTL."""
        ttl = ttl or self.default_ttl
        self.entries[key] = CacheEntry(key, value, ttl=ttl)
    
    def cleanup_expired(self) -> int:
        """Remove all expired entries. Returns count removed."""
        expired_keys = [
            k for k, entry in self.entries.items()
            if entry.is_expired()
        ]
        for k in expired_keys:
            del self.entries[k]
        return len(expired_keys)


class TemplateCache:
    """
    Main template caching system.
    
    Manages compilation cache, inheritance cache, and rendered output cache.
    """
    
    def __init__(self, max_size: int = 1000, strategy: CacheStrategy = CacheStrategy.LRU):
        self.strategy = strategy
        self.max_size = max_size
        
        # Create caches based on strategy
        if strategy == CacheStrategy.LRU:
            cache_class = LRUCache
        elif strategy == CacheStrategy.LFU:
            cache_class = LFUCache
        elif strategy == CacheStrategy.TTL:
            cache_class = TTLCache
        else:
            cache_class = LRUCache
        
        self.compilation_cache = cache_class(max_size // 3)  # 1/3 for compiled code
        self.inheritance_cache = cache_class(max_size // 3)  # 1/3 for chains
        self.render_cache = cache_class(max_size // 3)  # 1/3 for rendered output
    
    def get_compiled(self, template_name: str, template_content: str) -> Optional[str]:
        """Get compiled template code from cache."""
        key = CacheKey.for_compilation(template_name, template_content)
        return self.compilation_cache.get(key)
    
    def cache_compiled(self, template_name: str, template_content: str, 
                      compiled_code: str) -> None:
        """Cache compiled template code."""
        key = CacheKey.for_compilation(template_name, template_content)
        self.compilation_cache.set(key, compiled_code)
    
    def get_inheritance_chain(self, template_name: str, chain: List[str]) -> Optional[Any]:
        """Get cached inheritance chain."""
        key = CacheKey.for_inheritance_chain(template_name, chain)
        return self.inheritance_cache.get(key)
    
    def cache_inheritance_chain(self, template_name: str, chain: List[str], 
                               chain_obj: Any) -> None:
        """Cache inheritance chain resolution."""
        key = CacheKey.for_inheritance_chain(template_name, chain)
        self.inheritance_cache.set(key, chain_obj)
    
    def get_rendered(self, template_name: str, context: Dict[str, Any]) -> Optional[str]:
        """Get cached rendered output."""
        ctx_hash = CacheKey.context_hash(context)
        key = CacheKey.for_rendered(template_name, ctx_hash)
        return self.render_cache.get(key)
    
    def cache_rendered(self, template_name: str, context: Dict[str, Any], 
                      rendered_output: str) -> None:
        """Cache rendered template output."""
        ctx_hash = CacheKey.context_hash(context)
        key = CacheKey.for_rendered(template_name, ctx_hash)
        self.render_cache.set(key, rendered_output)
    
    def invalidate_template(self, template_name: str) -> None:
        """Invalidate all cache entries for template."""
        # Clear entries matching template name
        for cache in [self.compilation_cache, self.inheritance_cache, self.render_cache]:
            keys_to_delete = [
                k for k in cache.entries.keys()
                if template_name in k
            ]
            for k in keys_to_delete:
                cache.delete(k)
    
    def clear_all(self) -> None:
        """Clear all caches."""
        self.compilation_cache.clear()
        self.inheritance_cache.clear()
        self.render_cache.clear()
    
    def get_stats(self) -> Dict[str, CacheStats]:
        """Get statistics for all caches."""
        return {
            'compilation': self.compilation_cache.get_stats(),
            'inheritance': self.inheritance_cache.get_stats(),
            'render': self.render_cache.get_stats(),
        }
    
    def total_size(self) -> int:
        """Get total entries across all caches."""
        return (
            self.compilation_cache.size() +
            self.inheritance_cache.size() +
            self.render_cache.size()
        )


class CacheWarmer:
    """
    Pre-populates cache with commonly used templates.
    
    Improves initial request performance.
    """
    
    def __init__(self, cache: TemplateCache, compiler=None):
        self.cache = cache
        self.compiler = compiler
    
    async def warm_templates(self, template_list: List[Tuple[str, str]]) -> int:
        """
        Pre-compile templates and cache them.
        
        Args:
            template_list: List of (template_name, template_content) tuples
        
        Returns:
            Number of templates cached
        """
        if not self.compiler:
            return 0
        
        count = 0
        for template_name, template_content in template_list:
            try:
                # Compile template
                compiled = await self.compiler.compile(template_name, template_content)
                # Cache it
                self.cache.cache_compiled(template_name, template_content, compiled)
                count += 1
            except Exception:
                # Skip failed compilations
                pass
        
        return count


class CacheInvalidationStrategy:
    """
    Manages cache invalidation policies.
    
    - Manual: Explicit invalidation
    - Auto: Invalidate on dependency change
    - TTL: Time-based expiration
    """
    
    def __init__(self, cache: TemplateCache):
        self.cache = cache
        self.dependencies: Dict[str, Set[str]] = {}  # template -> set of dependent templates
    
    def register_dependency(self, template_name: str, depends_on: str) -> None:
        """Register template dependency."""
        if template_name not in self.dependencies:
            self.dependencies[template_name] = set()
        self.dependencies[template_name].add(depends_on)
    
    def invalidate_cascade(self, template_name: str) -> int:
        """
        Invalidate template and all dependents.
        
        Returns count of invalidated templates.
        """
        invalidated = {template_name}
        
        # Find all dependents
        for dependent, deps in self.dependencies.items():
            if template_name in deps:
                invalidated.add(dependent)
        
        # Invalidate all
        for name in invalidated:
            self.cache.invalidate_template(name)
        
        return len(invalidated)


# ================= Module Exports =================

__all__ = [
    'CacheStrategy',
    'CacheEntry',
    'CacheStats',
    'CacheKey',
    'BaseCache',
    'LRUCache',
    'LFUCache',
    'TTLCache',
    'TemplateCache',
    'CacheWarmer',
    'CacheInvalidationStrategy',
]
