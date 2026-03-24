"""
Tests for MetricsRegistry export formats (Issue #11).

Verifies:
1. Prometheus text format export for counters, gauges, histograms
2. JSON export format
3. Histogram bucketing works correctly
4. Labels handled properly in all formats
5. Reset clears all state
6. Counter increment, gauge set, histogram observe all work
"""

import pytest
from eden.core.metrics import MetricsRegistry, DEFAULT_BUCKETS


@pytest.fixture
def registry():
    """Fresh registry for each test."""
    return MetricsRegistry()


class TestCounters:
    """Test counter metric operations."""
    
    def test_increment_default(self, registry):
        """Increment with default value of 1."""
        registry.increment("requests_total")
        assert registry._counters["requests_total"] == 1
    
    def test_increment_custom_value(self, registry):
        """Increment by a custom amount."""
        registry.increment("bytes_sent", value=1024)
        assert registry._counters["bytes_sent"] == 1024
    
    def test_increment_accumulates(self, registry):
        """Multiple increments should accumulate."""
        registry.increment("requests_total")
        registry.increment("requests_total")
        registry.increment("requests_total", value=3)
        assert registry._counters["requests_total"] == 5
    
    def test_increment_with_labels(self, registry):
        """Counters with different labels should be separate."""
        registry.increment("requests_total", labels={"method": "GET"})
        registry.increment("requests_total", labels={"method": "POST"})
        registry.increment("requests_total", labels={"method": "GET"})
        
        assert registry._counters['requests_total{method=GET}'] == 2
        assert registry._counters['requests_total{method=POST}'] == 1


class TestGauges:
    """Test gauge metric operations."""
    
    def test_set_gauge(self, registry):
        """Setting a gauge should store the value."""
        registry.set_gauge("connections", 42)
        assert registry._gauges["connections"] == 42
    
    def test_set_gauge_overwrites(self, registry):
        """Setting a gauge twice should overwrite."""
        registry.set_gauge("connections", 42)
        registry.set_gauge("connections", 10)
        assert registry._gauges["connections"] == 10
    
    def test_gauge_with_labels(self, registry):
        """Gauges with different labels should be separate."""
        registry.set_gauge("temp", 72.5, labels={"location": "kitchen"})
        registry.set_gauge("temp", 68.0, labels={"location": "bedroom"})
        
        assert registry._gauges['temp{location=kitchen}'] == 72.5
        assert registry._gauges['temp{location=bedroom}'] == 68.0


class TestHistograms:
    """Test histogram metric operations with bucketing."""
    
    def test_observe_counts_and_sums(self, registry):
        """Observations should update count and sum."""
        registry.observe("response_time", 0.5)
        registry.observe("response_time", 1.5)
        registry.observe("response_time", 0.3)
        
        hist = registry._histograms["response_time"]
        assert hist["count"] == 3
        assert abs(hist["sum"] - 2.3) < 0.001
    
    def test_observe_buckets(self, registry):
        """Values should be placed in correct buckets (each bucket counts values <= bound)."""
        registry.observe("response_time", 0.003)  # <= 0.005, 0.01, ..., +Inf
        registry.observe("response_time", 0.5)     # <= 0.5, 1.0, ..., +Inf
        registry.observe("response_time", 5.0)     # <= 5.0, 10.0, +Inf
        registry.observe("response_time", 100.0)   # <= +Inf only
        
        buckets = registry._histograms["response_time"]["buckets"]
        # 0.003 fits in all buckets >= 0.005
        assert buckets[0.005] == 1   # 0.003
        # 0.003 and 0.5 both fit in 0.5 bucket
        assert buckets[0.5] == 2     # 0.003 + 0.5
        # 0.003, 0.5, and 5.0 all fit in 5.0 bucket 
        assert buckets[5.0] == 3     # 0.003 + 0.5 + 5.0
        # +Inf bucket captures ALL values (any value <= +Inf)
        assert buckets[float("inf")] == 4  # all values
    
    def test_observe_with_labels(self, registry):
        """Histograms with different labels should be separate."""
        registry.observe("response_time", 0.1, labels={"endpoint": "/api"})
        registry.observe("response_time", 2.0, labels={"endpoint": "/web"})
        
        assert "response_time{endpoint=/api}" in registry._histograms
        assert "response_time{endpoint=/web}" in registry._histograms


class TestPrometheusExport:
    """Test Prometheus text format export."""
    
    def test_counter_export(self, registry):
        """Counters should export with TYPE header."""
        registry.increment("http_requests_total", labels={"method": "GET"})
        output = registry.export_prometheus()
        
        assert "# TYPE http_requests_total counter" in output
        assert 'http_requests_total{method="GET"} 1' in output
    
    def test_gauge_export(self, registry):
        """Gauges should export with TYPE header."""
        registry.set_gauge("active_connections", 5)
        output = registry.export_prometheus()
        
        assert "# TYPE active_connections gauge" in output
        assert "active_connections 5" in output
    
    def test_histogram_export(self, registry):
        """Histograms should export with buckets, sum, and count."""
        registry.observe("response_time_seconds", 0.25)
        registry.observe("response_time_seconds", 1.0)
        output = registry.export_prometheus()
        
        assert "# TYPE response_time_seconds histogram" in output
        assert "response_time_seconds_sum" in output
        assert "response_time_seconds_count 2" in output
        # Should have bucket lines
        assert 'response_time_seconds_bucket{le="+Inf"}' in output
    
    def test_empty_export(self, registry):
        """Empty registry should produce empty string."""
        output = registry.export_prometheus()
        assert output == ""
    
    def test_multiple_metrics_export(self, registry):
        """Multiple metric types should all appear in output."""
        registry.increment("req_total")
        registry.set_gauge("active", 3)
        registry.observe("latency", 0.1)
        output = registry.export_prometheus()
        
        assert "req_total" in output
        assert "active" in output
        assert "latency" in output


class TestJSONExport:
    """Test JSON export format."""
    
    def test_json_export_structure(self, registry):
        """JSON export should have counters, gauges, histograms keys."""
        registry.increment("requests")
        registry.set_gauge("connections", 10)
        registry.observe("latency", 0.5)
        
        data = registry.export_json()
        assert "counters" in data
        assert "gauges" in data
        assert "histograms" in data
    
    def test_json_counters(self, registry):
        """JSON counters should be a flat dict."""
        registry.increment("a", value=5)
        data = registry.export_json()
        assert data["counters"]["a"] == 5
    
    def test_json_histograms_computed_fields(self, registry):
        """JSON histograms should include count, sum, avg."""
        registry.observe("latency", 1.0)
        registry.observe("latency", 3.0)
        
        data = registry.export_json()
        hist = data["histograms"]["latency"]
        assert hist["count"] == 2
        assert hist["sum"] == 4.0
        assert hist["avg"] == 2.0


class TestReset:
    """Test reset functionality."""
    
    def test_reset_clears_all(self, registry):
        """Reset should clear counters, gauges, and histograms."""
        registry.increment("a")
        registry.set_gauge("b", 10)
        registry.observe("c", 0.5)
        
        registry.reset()
        
        assert len(registry._counters) == 0
        assert len(registry._gauges) == 0
        assert len(registry._histograms) == 0
    
    def test_reset_allows_re_use(self, registry):
        """After reset, metrics can be collected again from zero."""
        registry.increment("a", value=100)
        registry.reset()
        registry.increment("a", value=1)
        
        assert registry._counters["a"] == 1
