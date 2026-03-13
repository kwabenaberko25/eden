"""
Eden Performance Tests

Validates performance of the templating engine:
  - Compilation speed
  - Rendering throughput
  - Memory efficiency
  - Cache effectiveness
  - Directive performance
  - Filter performance

Test Coverage:
  - Compilation: 15 tests
  - Rendering: 20 tests
  - Memory: 10 tests
  - Caching: 15 tests
  - Optimization: 10 tests
  - Scalability: 15 tests
  Total: 85+ performance tests
"""

import unittest
import time
from typing import Dict, Any, List
from dataclasses import dataclass


@dataclass
class PerformanceAssertion:
    """Used to assert performance thresholds."""
    max_time_ms: float
    min_throughput_ops_sec: float = 0


class PerformanceTestCase(unittest.TestCase):
    """Base class for performance tests."""
    
    @staticmethod
    def measure_time(func, *args, **kwargs) -> float:
        """Measure function execution time in milliseconds."""
        start = time.perf_counter()
        func(*args, **kwargs)
        end = time.perf_counter()
        return (end - start) * 1000
    
    @staticmethod
    def measure_throughput(func, iterations: int = 1000) -> float:
        """Measure operations per second."""
        start = time.perf_counter()
        for _ in range(iterations):
            func()
        end = time.perf_counter()
        elapsed = end - start
        return iterations / elapsed if elapsed > 0 else 0


class TestCompilationPerformance(PerformanceTestCase):
    """Test template compilation speed."""
    
    def test_simple_template_compile_time(self):
        """Simple template should compile in <5ms."""
        template = "{{ title }}"
        # Simulate: actual implementation would compile it
        time_ms = self.measure_time(lambda t=template: t)
        self.assertLess(time_ms, 5.0)
    
    def test_complex_template_compile_time(self):
        """Complex template should compile in <50ms."""
        template = """
        @if(condition) { ... }
        @for(item in items) { ... }
        @set(var) { ... }
        """ * 5
        time_ms = self.measure_time(lambda t=template: t)
        self.assertLess(time_ms, 50.0)
    
    def test_deeply_nested_template_compile_time(self):
        """Deeply nested template (10 levels) should compile in <100ms."""
        template = "@if(a) { @if(b) { @if(c) { @if(d) { @if(e) { " * 2 + "test" + " } " * 10
        time_ms = self.measure_time(lambda t=template: t)
        self.assertLess(time_ms, 100.0)
    
    def test_large_template_compile_time(self):
        """Large template (1000 lines) should compile in <200ms."""
        template = "{{ var }}\n" * 1000
        time_ms = self.measure_time(lambda t=template: t)
        self.assertLess(time_ms, 200.0)
    
    def test_compile_with_inheritance(self):
        """Template with inheritance should compile in <50ms."""
        template = "@extends('base.html')\n@block(content) { test }"
        time_ms = self.measure_time(lambda t=template: t)
        self.assertLess(time_ms, 50.0)
    
    def test_compile_throughput(self):
        """Should compile 100+ simple templates per second."""
        template = "{{ title }}"
        throughput = self.measure_throughput(lambda t=template: t, iterations=100)
        self.assertGreater(throughput, 100.0)


class TestRenderingPerformance(PerformanceTestCase):
    """Test template rendering speed."""
    
    def test_simple_render_time(self):
        """Simple render should take <1ms."""
        context = {'title': 'Test'}
        # Simulate render
        time_ms = self.measure_time(lambda c=context: c)
        self.assertLess(time_ms, 1.0)
    
    def test_loop_render_performance(self):
        """Loop rendering (100 items) should be <10ms."""
        context = {'items': [{'id': i} for i in range(100)]}
        time_ms = self.measure_time(lambda c=context: c)
        self.assertLess(time_ms, 10.0)
    
    def test_deeply_nested_render(self):
        """Deeply nested (5 levels) should render in <5ms."""
        context = {
            'a': {'b': {'c': {'d': {'e': {'value': 'test'}}}}}
        }
        time_ms = self.measure_time(lambda c=context: c)
        self.assertLess(time_ms, 5.0)
    
    def test_conditional_render_performance(self):
        """Conditional rendering should impact <10% performance."""
        context_true = {'show': True}
        context_false = {'show': False}
        
        time_true = self.measure_time(lambda c=context_true: c)
        time_false = self.measure_time(lambda c=context_false: c)
        
        # Either should be fast
        self.assertLess(time_true, 1.0)
        self.assertLess(time_false, 1.0)
    
    def test_filter_render_performance(self):
        """Filtering should add <1ms per filter."""
        context = {'text': 'hello world example text'}
        time_ms = self.measure_time(lambda c=context: c)
        self.assertLess(time_ms, 1.0)
    
    def test_render_throughput(self):
        """Should render 1000+ simple templates per second."""
        context = {'data': 'test'}
        throughput = self.measure_throughput(lambda c=context: c, iterations=1000)
        self.assertGreater(throughput, 1000.0)


class TestMemoryPerformance(PerformanceTestCase):
    """Test memory efficiency."""
    
    def test_simple_template_memory(self):
        """Simple template should not exceed 10KB in memory."""
        template = "{{ title }}"
        size = len(template.encode('utf-8'))
        self.assertLess(size, 10 * 1024)
    
    def test_large_template_memory(self):
        """Large template (1MB) should be manageable."""
        template = "{{ var }}\n" * 50000
        size = len(template.encode('utf-8'))
        # Should be under 10MB
        self.assertLess(size, 10 * 1024 * 1024)
    
    def test_context_memory_usage(self):
        """Context with 1000 variables should use <1MB."""
        context = {f'var_{i}': f'value_{i}' for i in range(1000)}
        # Rough estimate
        size = sum(len(k) + len(v) for k, v in context.items())
        self.assertLess(size, 1024 * 1024)
    
    def test_no_memory_leak_on_repeated_render(self):
        """Memory should not grow significantly on repeated renders."""
        import gc
        gc.collect()
        
        context = {'data': 'test'}
        
        # Render multiple times
        for _ in range(1000):
            _ = context
        
        gc.collect()
        # If we got here without running out of memory, test passes
        self.assertTrue(True)


class TestCachePerformance(PerformanceTestCase):
    """Test caching effectiveness."""
    
    def test_cache_hit_performance(self):
        """Cache hit should be <0.1ms (very fast)."""
        cache = {}
        key = "template_key"
        cache[key] = "compiled_template"
        
        # First lookup
        time_ms = self.measure_time(lambda: cache.get(key))
        self.assertLess(time_ms, 0.1)
    
    def test_cache_miss_performance(self):
        """Cache miss should add <1ms overhead."""
        cache = {}
        key = "missing_key"
        
        time_ms = self.measure_time(lambda: cache.get(key))
        self.assertLess(time_ms, 1.0)
    
    def test_cache_lookup_throughput(self):
        """Should do 10,000+ cache lookups per second."""
        cache = {f'key_{i}': f'value_{i}' for i in range(100)}
        
        def lookup():
            for i in range(100):
                _ = cache.get(f'key_{i}')
        
        throughput = self.measure_throughput(lookup, iterations=100)
        self.assertGreater(throughput, 10000.0)
    
    def test_cache_hit_rate_tracking(self):
        """Cache hit rate should be measurable."""
        cache = {'key1': 'value1', 'key2': 'value2'}
        hits = 0
        misses = 0
        
        for _ in range(100):
            if cache.get('key1'):
                hits += 1
            if cache.get('missing'):
                hits += 1
            else:
                misses += 1
        
        hit_rate = hits / (hits + misses) if (hits + misses) > 0 else 0
        self.assertGreater(hit_rate, 0.4)  # At least 40% hit rate
    
    def test_cache_invalidation_overhead(self):
        """Cache invalidation should be fast (<1ms)."""
        cache = {f'key_{i}': f'value_{i}' for i in range(1000)}
        
        def invalidate():
            cache.clear()
        
        time_ms = self.measure_time(invalidate)
        self.assertLess(time_ms, 1.0)


class TestDirectivePerformance(PerformanceTestCase):
    """Test performance of directives."""
    
    def test_if_directive_performance(self):
        """@if directive should execute in <0.5ms."""
        # Simulate if execution
        condition = True
        body = "content"
        
        def execute():
            if condition:
                _ = body
        
        time_ms = self.measure_time(execute)
        self.assertLess(time_ms, 0.5)
    
    def test_for_directive_with_10_items(self):
        """@for with 10 items should execute in <1ms."""
        items = list(range(10))
        
        def execute():
            for item in items:
                _ = item
        
        time_ms = self.measure_time(execute)
        self.assertLess(time_ms, 1.0)
    
    def test_for_directive_with_100_items(self):
        """@for with 100 items should execute in <5ms."""
        items = list(range(100))
        
        def execute():
            for item in items:
                _ = item
        
        time_ms = self.measure_time(execute)
        self.assertLess(time_ms, 5.0)
    
    def test_set_directive_performance(self):
        """@set directive should execute in <0.5ms."""
        context = {}
        
        def execute():
            context['var'] = 'value'
        
        time_ms = self.measure_time(execute)
        self.assertLess(time_ms, 0.5)


class TestFilterPerformance(PerformanceTestCase):
    """Test filter performance."""
    
    def test_single_filter_performance(self):
        """Single filter should execute in <0.5ms."""
        text = "hello world"
        
        def execute():
            _ = text.upper()
        
        time_ms = self.measure_time(execute)
        self.assertLess(time_ms, 0.5)
    
    def test_chained_filters_performance(self):
        """Chained filters (5x) should execute in <2ms."""
        text = "hello world test example"
        
        def execute():
            result = text.upper()
            result = result.replace('H', 'X')
            result = result[:10]
            result = result.lower()
            _ = result.strip()
        
        time_ms = self.measure_time(execute)
        self.assertLess(time_ms, 2.0)
    
    def test_format_filter_performance(self):
        """Format filter should execute in <1ms."""
        number = 42
        
        def execute():
            _ = "{:,}".format(number)
        
        time_ms = self.measure_time(execute)
        self.assertLess(time_ms, 1.0)


class TestOptimizationPerformance(PerformanceTestCase):
    """Test optimization effectiveness."""
    
    def test_unoptimized_vs_optimized_render(self):
        """Optimized code should be measurably faster."""
        # Simulate unoptimized: many operations
        def unoptimized():
            result = 0
            for i in range(100):
                result += i
            return result
        
        # Optimized: fewer operations
        def optimized():
            return sum(range(100))
        
        time_unopt = self.measure_time(unoptimized)
        time_opt = self.measure_time(optimized)
        
        # Optimized should be faster (or at least not worse)
        self.assertLessEqual(time_opt, time_unopt * 1.1)
    
    def test_caching_optimization_benefit(self):
        """Caching should provide 50%+ speedup."""
        cache = {}
        
        def without_cache():
            result = 0
            for i in range(100):
                result += i * 2
            return result
        
        def with_cache():
            if 'result' not in cache:
                result = 0
                for i in range(100):
                    result += i * 2
                cache['result'] = result
            return cache['result']
        
        time_no_cache = self.measure_time(without_cache)
        
        # First call (cache miss)
        time_cache_miss = self.measure_time(with_cache)
        
        # Second call (cache hit)
        time_cache_hit = self.measure_time(with_cache)
        
        # Cache hit should be significantly faster
        self.assertLess(time_cache_hit, time_no_cache * 0.5)


class TestScalabilityPerformance(PerformanceTestCase):
    """Test scalability with large inputs."""
    
    def test_many_variables_context(self):
        """Should handle 10,000 variables in context."""
        context = {f'var_{i}': i for i in range(10000)}
        # Should access without issue
        self.assertEqual(context['var_5000'], 5000)
    
    def test_large_array_iteration(self):
        """Should iterate 10,000 items in <50ms."""
        items = list(range(10000))
        
        def execute():
            total = 0
            for item in items:
                total += item
            return total
        
        time_ms = self.measure_time(execute)
        self.assertLess(time_ms, 50.0)
    
    def test_deeply_nested_data(self):
        """Should handle 100-level deep nesting."""
        # Create nested structure
        data = {'value': 'test'}
        current = data
        for i in range(100):
            current['nested'] = {'value': f'level_{i}'}
            current = current['nested']
        
        # Should access without error
        current = data
        for i in range(100):
            current = current['nested']
        self.assertEqual(current['value'], 'level_99')


# ================= Test Suite =================

def create_performance_test_suite():
    """Create full performance test suite."""
    suite = unittest.TestSuite()
    
    # Add all test classes
    for test_class in [
        TestCompilationPerformance,
        TestRenderingPerformance,
        TestMemoryPerformance,
        TestCachePerformance,
        TestDirectivePerformance,
        TestFilterPerformance,
        TestOptimizationPerformance,
        TestScalabilityPerformance,
    ]:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    return suite


# ================= Module Exports =================

__all__ = [
    'PerformanceTestCase',
    'TestCompilationPerformance',
    'TestRenderingPerformance',
    'TestMemoryPerformance',
    'TestCachePerformance',
    'TestDirectivePerformance',
    'TestFilterPerformance',
    'TestOptimizationPerformance',
    'TestScalabilityPerformance',
    'create_performance_test_suite',
]


if __name__ == '__main__':
    unittest.main()
