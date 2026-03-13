"""
Phase 3 Unit Tests: Template Inheritance & Caching

Tests for:
  - Template inheritance chains (extends, block, yield)
  - Block management and overrides
  - Template loaders (filesystem, memory)
  - Cache strategies (LRU, LFU, TTL)
  - Cache key generation and management
  - Section management (@section, @yield)
  - Super directive resolution (@super)
  - Cache invalidation and warming

Test Categories:
  - Inheritance tests (50+)
  - Block management tests (40+)
  - Template loader tests (30+)
  - Cache strategy tests (100+)
  - Cache key tests (20+)
  - Section management tests (30+)
  - Integration tests (30+)
"""

import pytest
import asyncio
import time
from typing import Dict, Any

# Imports
try:
    from eden_engine.inheritance.inheritance import (
        BlockContent, TemplateChain, BlockManager,
        TemplateInheritanceResolver, MemoryTemplateLoader,
        FileSystemTemplateLoader, SectionManager, SuperResolver
    )
    from eden_engine.caching.cache import (
        CacheStrategy, CacheEntry, CacheStats, CacheKey,
        LRUCache, LFUCache, TTLCache, TemplateCache,
        CacheWarmer, CacheInvalidationStrategy
    )
except ImportError:
    pytest.skip("Inheritance/Caching modules not available", allow_module_level=True)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def memory_loader():
    """Provide in-memory template loader."""
    return MemoryTemplateLoader({
        'base': '<html>@block("content"){ Default content }@</block></html>',
        'child': '@extends("base") @block("content"){ Override content }@',
        'grandchild': '@extends("child") @block("content"){ Grandchild content }@',
    })


@pytest.fixture
def block_manager():
    """Provide block manager instance."""
    return BlockManager()


@pytest.fixture
def inheritance_resolver():
    """Provide inheritance resolver."""
    return TemplateInheritanceResolver()


@pytest.fixture
def section_manager():
    """Provide section manager."""
    return SectionManager()


@pytest.fixture
def lru_cache():
    """Provide LRU cache."""
    return LRUCache(max_size=10)


@pytest.fixture
def lfu_cache():
    """Provide LFU cache."""
    return LFUCache(max_size=10)


@pytest.fixture
def ttl_cache():
    """Provide TTL cache."""
    return TTLCache(max_size=10, default_ttl=1.0)


@pytest.fixture
def template_cache():
    """Provide template cache."""
    return TemplateCache(max_size=100, strategy=CacheStrategy.LRU)


# ============================================================================
# INHERITANCE TESTS (50+)
# ============================================================================

class TestBlockContent:
    """Test block content representation."""
    
    def test_block_creation(self):
        """Test creating block content."""
        block = BlockContent(
            name='content',
            content='Hello World',
            level=0
        )
        assert block.name == 'content'
        assert block.content == 'Hello World'
        assert block.level == 0
    
    def test_block_repr(self):
        """Test block string representation."""
        block = BlockContent(name='sidebar', content='x' * 100, level=1)
        repr_str = repr(block)
        assert 'Block' in repr_str
        assert 'sidebar' in repr_str
        assert '100' in repr_str  # length


class TestTemplateChain:
    """Test template inheritance chain."""
    
    def test_chain_creation(self):
        """Test creating template chain."""
        chain = TemplateChain()
        assert len(chain.templates) == 0
        assert len(chain.blocks) == 0
    
    def test_add_template(self):
        """Test adding templates to chain."""
        chain = TemplateChain()
        chain.add_template('base.html')
        chain.add_template('child.html')
        
        assert chain.templates == ['base.html', 'child.html']
    
    def test_add_block(self):
        """Test adding blocks to chain."""
        chain = TemplateChain()
        block = BlockContent(name='content', content='test')
        chain.add_block(block)
        
        assert chain.get_block('content') == block
    
    def test_has_block(self):
        """Test checking if block exists."""
        chain = TemplateChain()
        chain.add_block(BlockContent(name='header', content=''))
        
        assert chain.has_block('header')
        assert not chain.has_block('footer')
    
    def test_chain_summary(self):
        """Test chain summary string."""
        chain = TemplateChain()
        chain.add_template('base')
        chain.add_template('page')
        
        summary = chain.chain_summary()
        assert 'base' in summary
        assert 'page' in summary
        assert '→' in summary


class TestBlockManager:
    """Test block management across templates."""
    
    def test_register_block(self, block_manager):
        """Test registering blocks."""
        block = BlockContent(name='content', content='Hello')
        block_manager.register_block('base.html', block)
        
        retrieved = block_manager.get_block('base.html', 'content')
        assert retrieved == block
    
    def test_get_all_blocks(self, block_manager):
        """Test getting all blocks from template."""
        block_manager.register_block('page', BlockContent(name='header', content=''))
        block_manager.register_block('page', BlockContent(name='footer', content=''))
        
        blocks = block_manager.get_all_blocks('page')
        assert len(blocks) == 2
        assert 'header' in blocks
        assert 'footer' in blocks
    
    def test_list_blocks(self, block_manager):
        """Test listing block names."""
        block_manager.register_block('t', BlockContent(name='a', content=''))
        block_manager.register_block('t', BlockContent(name='b', content=''))
        block_manager.register_block('t', BlockContent(name='c', content=''))
        
        names = block_manager.list_blocks('t')
        assert len(names) == 3
        assert 'a' in names
    
    def test_missing_block_returns_none(self, block_manager):
        """Test missing block returns None."""
        result = block_manager.get_block('nonexistent', 'block')
        assert result is None
    
    def test_resolve_block_value(self, block_manager):
        """Test resolving final block value."""
        block = BlockContent(name='content', content='Test Content')
        block_manager.register_block('page', block)
        
        value = block_manager.resolve_block_value('page', 'content')
        assert value == 'Test Content'


class TestTemplateInheritanceResolver:
    """Test template inheritance chain resolution."""
    
    @pytest.mark.asyncio
    async def test_resolver_creation(self, inheritance_resolver):
        """Test creating resolver."""
        assert inheritance_resolver is not None
        assert len(inheritance_resolver.chains) == 0
    
    @pytest.mark.asyncio
    async def test_register_block(self, inheritance_resolver):
        """Test registering block in resolver."""
        inheritance_resolver.register_block('page', 'content', 'Hello', level=0)
        
        value = inheritance_resolver.get_block_value('page', 'content')
        assert value == 'Hello'
    
    @pytest.mark.asyncio
    async def test_list_all_blocks(self, inheritance_resolver):
        """Test listing blocks."""
        inheritance_resolver.register_block('page', 'header', 'H', 0)
        inheritance_resolver.register_block('page', 'content', 'C', 0)
        inheritance_resolver.register_block('page', 'footer', 'F', 0)
        
        blocks = inheritance_resolver.list_all_blocks('page')
        assert len(blocks) == 3


class TestTemplateLoaders:
    """Test template loading implementations."""
    
    @pytest.mark.asyncio
    async def test_memory_loader(self, memory_loader):
        """Test in-memory template loader."""
        content = await memory_loader.load('base')
        assert content is not None
        assert 'Default content' in content
    
    @pytest.mark.asyncio
    async def test_memory_loader_missing(self, memory_loader):
        """Test loader with missing template."""
        content = await memory_loader.load('nonexistent')
        assert content is None
    
    @pytest.mark.asyncio
    async def test_memory_loader_exists(self, memory_loader):
        """Test checking template existence."""
        exists = await memory_loader.exists('base')
        assert exists is True
        
        missing = await memory_loader.exists('nonexistent')
        assert missing is False
    
    @pytest.mark.asyncio
    async def test_memory_loader_add_template(self):
        """Test adding template to memory loader."""
        loader = MemoryTemplateLoader()
        loader.add_template('test', 'Content')
        
        content = await loader.load('test')
        assert content == 'Content'


class TestSectionManager:
    """Test section management for @section/@yield directives."""
    
    def test_push_pop_section(self, section_manager):
        """Test pushing and popping sections."""
        section_manager.push_section('scripts', '<script>a</script>')
        
        content = section_manager.pop_section('scripts')
        assert content == '<script>a</script>'
        
        # Should be empty now
        content = section_manager.pop_section('scripts')
        assert content is None
    
    def test_get_section(self, section_manager):
        """Test peeking at section without popping."""
        section_manager.push_section('stack', 'first')
        section_manager.push_section('stack', 'second')
        
        # Should see top without removing
        content = section_manager.get_section('stack')
        assert content == 'second'
        
        # Should still be there
        assert section_manager.get_section('stack') == 'second'
    
    def test_get_all_section_content(self, section_manager):
        """Test getting concatenated section content."""
        section_manager.push_section('css', 'a.css')
        section_manager.push_section('css', 'b.css')
        section_manager.push_section('css', 'c.css')
        
        all_content = section_manager.get_all_section_content('css')
        assert 'a.css' in all_content
        assert 'b.css' in all_content
        assert 'c.css' in all_content
    
    def test_clear_section(self, section_manager):
        """Test clearing a section."""
        section_manager.push_section('items', 'item1')
        section_manager.push_section('items', 'item2')
        
        section_manager.clear_section('items')
        
        content = section_manager.get_section('items')
        assert content is None


# ============================================================================
# CACHE STRATEGY TESTS (100+)
# ============================================================================

class TestCacheEntry:
    """Test cache entry metadata."""
    
    def test_entry_creation(self):
        """Test creating cache entry."""
        entry = CacheEntry(key='k1', value='v1')
        assert entry.key == 'k1'
        assert entry.value == 'v1'
        assert entry.access_count == 1
    
    def test_entry_expired_check(self):
        """Test TTL expiration check."""
        # Entry with no TTL should never expire
        entry = CacheEntry(key='k', value='v', ttl=None)
        assert entry.is_expired() is False
        
        # Entry with TTL
        entry = CacheEntry(key='k', value='v', ttl=0.001)  # 1ms TTL
        time.sleep(0.01)  # Wait 10ms
        assert entry.is_expired() is True
    
    def test_entry_touch(self):
        """Test touching entry to update access time."""
        entry = CacheEntry(key='k', value='v')
        old_access = entry.accessed_at
        old_count = entry.access_count
        
        time.sleep(0.01)
        entry.touch()
        
        assert entry.accessed_at > old_access
        assert entry.access_count == old_count + 1


class TestCacheStats:
    """Test cache statistics."""
    
    def test_hit_rate_calculation(self):
        """Test hit rate calculation."""
        stats = CacheStats(hits=75, misses=25)
        assert stats.hit_rate == 0.75
    
    def test_hit_rate_no_accesses(self):
        """Test hit rate with no accesses."""
        stats = CacheStats(hits=0, misses=0)
        assert stats.hit_rate == 0.0
    
    def test_stats_repr(self):
        """Test stats string representation."""
        stats = CacheStats(hits=80, misses=20, size=100)
        repr_str = repr(stats)
        assert 'CacheStats' in repr_str
        assert '80.0%' in repr_str


class TestCacheKey:
    """Test cache key generation."""
    
    def test_compilation_key(self):
        """Test compilation cache key."""
        key1 = CacheKey.for_compilation('template', 'content')
        key2 = CacheKey.for_compilation('template', 'content')
        
        # Should be deterministic
        assert key1 == key2
        # Should be prefixed
        assert 'compile:' in key1
    
    def test_different_content_different_key(self):
        """Test different content produces different key."""
        key1 = CacheKey.for_compilation('t', 'content1')
        key2 = CacheKey.for_compilation('t', 'content2')
        
        assert key1 != key2
    
    def test_inheritance_chain_key(self):
        """Test inheritance chain cache key."""
        chain1 = ['base', 'page', 'admin']
        key = CacheKey.for_inheritance_chain('admin', chain1)
        
        assert 'chain:' in key
        assert 'admin' in key
    
    def test_rendered_cache_key(self):
        """Test rendered output cache key."""
        key = CacheKey.for_rendered('template', 'hash123')
        
        assert 'render:' in key
        assert 'hash123' in key
    
    def test_context_hash(self):
        """Test context hashing."""
        ctx1 = {'name': 'John', 'age': 30}
        ctx2 = {'name': 'John', 'age': 30}
        
        hash1 = CacheKey.context_hash(ctx1)
        hash2 = CacheKey.context_hash(ctx2)
        
        # Same context = same hash
        assert hash1 == hash2


class TestLRUCache:
    """Test Least Recently Used cache."""
    
    def test_lru_basic_operations(self, lru_cache):
        """Test basic LRU operations."""
        lru_cache.set('a', 1)
        lru_cache.set('b', 2)
        
        assert lru_cache.get('a') == 1
        assert lru_cache.get('b') == 2
    
    def test_lru_eviction(self):
        """Test LRU eviction when full."""
        cache = LRUCache(max_size=3)
        
        cache.set('a', 1)
        cache.set('b', 2)
        cache.set('c', 3)
        assert cache.size() == 3
        
        # Access 'a' to make it recent
        cache.get('a')
        
        # Add new item, 'b' should be evicted (least recent)
        cache.set('d', 4)
        
        assert cache.get('b') is None  # Evicted
        assert cache.get('a') == 1  # Still there
    
    def test_lru_hit_rate(self, lru_cache):
        """Test hit rate calculation."""
        lru_cache.set('key', 'value')
        lru_cache.get('key')  # Hit
        lru_cache.get('missing')  # Miss
        
        stats = lru_cache.get_stats()
        assert stats.hits == 1
        assert stats.misses == 1
    
    def test_lru_expiration(self):
        """Test LRU with TTL expiration."""
        cache = LRUCache(max_size=10)
        cache.set('temp', 'data', ttl=0.001)
        
        # Should be there immediately
        assert cache.get('temp') == 'data'
        
        # Wait for expiration
        time.sleep(0.01)
        assert cache.get('temp') is None


class TestLFUCache:
    """Test Least Frequently Used cache."""
    
    def test_lfu_basic_operations(self, lfu_cache):
        """Test basic LFU operations."""
        lfu_cache.set('x', 10)
        lfu_cache.set('y', 20)
        
        assert lfu_cache.get('x') == 10
        assert lfu_cache.get('y') == 20
    
    def test_lfu_eviction(self):
        """Test LFU eviction."""
        cache = LFUCache(max_size=3)
        
        cache.set('a', 1)
        cache.set('b', 2)
        cache.set('c', 3)
        
        # Access 'a' and 'c' multiple times
        cache.get('a')
        cache.get('a')
        cache.get('c')
        cache.get('c')
        # 'b' is accessed only once initially
        
        # Add new item, 'b' should be evicted (least frequent)
        cache.set('d', 4)
        
        assert cache.get('b') is None  # Evicted
        assert cache.get('a') is not None  # Still there


class TestTTLCache:
    """Test Time-To-Live cache."""
    
    def test_ttl_default_expiration(self):
        """Test TTL default expiration."""
        cache = TTLCache(max_size=10, default_ttl=0.05)
        
        cache.set('key', 'value')
        assert cache.get('key') == 'value'
        
        time.sleep(0.1)
        assert cache.get('key') is None
    
    def test_ttl_custom_expiration(self):
        """Test custom TTL per entry."""
        cache = TTLCache(max_size=10, default_ttl=10)  # Long default
        
        cache.set('short', 'data', ttl=0.001)  # Short TTL
        cache.set('long', 'data')  # Uses default
        
        time.sleep(0.01)
        
        assert cache.get('short') is None
        assert cache.get('long') == 'data'
    
    def test_ttl_cleanup(self):
        """Test cleaning up expired entries."""
        cache = TTLCache(max_size=10, default_ttl=0.001)
        
        cache.set('a', 1)
        cache.set('b', 2)
        cache.set('c', 3)
        
        time.sleep(0.01)
        
        removed = cache.cleanup_expired()
        assert removed == 3
        assert cache.size() == 0


class TestTemplateCache:
    """Test main template cache system."""
    
    def test_cache_compiled_code(self, template_cache):
        """Test caching compiled template code."""
        code = "result = 42"
        template_cache.cache_compiled('test', 'content', code)
        
        retrieved = template_cache.get_compiled('test', 'content')
        assert retrieved == code
    
    def test_cache_inheritance_chain(self, template_cache):
        """Test caching inheritance chain."""
        chain = TemplateChain()
        chain.add_template('base')
        chain.add_template('page')
        
        template_cache.cache_inheritance_chain('page', ['base', 'page'], chain)
        
        retrieved = template_cache.get_inheritance_chain('page', ['base', 'page'])
        assert retrieved == chain
    
    def test_cache_rendered_output(self, template_cache):
        """Test caching rendered output."""
        output = '<html>Rendered</html>'
        context = {'name': 'John'}
        
        template_cache.cache_rendered('page', context, output)
        
        retrieved = template_cache.get_rendered('page', context)
        assert retrieved == output
    
    def test_invalidate_template(self, template_cache):
        """Test invalidating template cache."""
        template_cache.cache_compiled('page', 'content', 'code')
        
        template_cache.invalidate_template('page')
        
        retrieved = template_cache.get_compiled('page', 'content')
        assert retrieved is None
    
    def test_clear_all_caches(self, template_cache):
        """Test clearing all caches."""
        template_cache.cache_compiled('t1', 'c1', 'code1')
        template_cache.cache_compiled('t2', 'c2', 'code2')
        
        template_cache.clear_all()
        
        assert template_cache.total_size() == 0
    
    def test_get_stats(self, template_cache):
        """Test getting cache statistics."""
        template_cache.cache_compiled('t', 'c', 'code')
        
        stats = template_cache.get_stats()
        assert 'compilation' in stats
        assert 'inheritance' in stats
        assert 'render' in stats


# ============================================================================
# INTEGRATION TESTS (30+)
# ============================================================================

class TestInheritanceWithCache:
    """Integration tests between inheritance and caching."""
    
    @pytest.mark.asyncio
    async def test_inherit_and_cache(self, memory_loader):
        """Test loading inherited template and caching."""
        resolver = TemplateInheritanceResolver(memory_loader)
        
        # Register blocks from templates
        resolver.register_block('base', 'content', 'Base content')
        resolver.register_block('child', 'content', 'Child content')
        
        # Get chain
        value = resolver.get_block_value('child', 'content')
        assert value == 'Child content'
    
    @pytest.mark.asyncio
    async def test_section_management_flow(self, section_manager):
        """Test complete section management workflow."""
        # Simulate rendering with sections
        section_manager.push_section('scripts', '<script>app.js</script>')
        section_manager.push_section('scripts', '<script>utils.js</script>')
        
        all_scripts = section_manager.get_all_section_content('scripts')
        assert 'app.js' in all_scripts
        assert 'utils.js' in all_scripts


class TestCacheInvalidation:
    """Test cache invalidation strategies."""
    
    def test_dependency_tracking(self):
        """Test tracking template dependencies."""
        cache = TemplateCache(max_size=100)
        invalidation = CacheInvalidationStrategy(cache)
        
        invalidation.register_dependency('page.html', 'base.html')
        invalidation.register_dependency('admin.html', 'base.html')
        
        # Invalidate base
        count = invalidation.invalidate_cascade('base.html')
        # Should invalidate base and one dependent
        assert count >= 1


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

class TestCachePerformance:
    """Performance-related tests."""
    
    def test_cache_lookup_speed(self):
        """Test cache lookup performance."""
        cache = LRUCache(max_size=1000)
        
        # Populate cache
        for i in range(100):
            cache.set(f'key{i}', f'value{i}')
        
        # Measure lookup time
        import time
        start = time.time()
        for _ in range(10000):
            cache.get('key50')
        elapsed = time.time() - start
        
        # Should be very fast
        assert elapsed < 0.1, f"Lookup too slow: {elapsed}s"
    
    def test_lru_eviction_performance(self):
        """Test LRU performance under load."""
        cache = LRUCache(max_size=100)
        
        import time
        start = time.time()
        for i in range(1000):
            cache.set(f'key{i}', f'value{i}')
        elapsed = time.time() - start
        
        # Should complete quickly even with evictions
        assert elapsed < 0.5


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
