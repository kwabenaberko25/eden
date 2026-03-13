# Eden Templating Engine - Deployment Guide

**Last Updated:** March 13, 2026  
**Version:** 1.0.0  
**Status:** Production Ready ✅

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Integration](#integration)
5. [Performance Tuning](#performance-tuning)
6. [Security Setup](#security-setup)
7. [Monitoring](#monitoring)
8. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Minimal Setup (5 minutes)

```bash
# 1. Install dependencies
pip install lark simpleeval markupsafe

# 2. Create a simple template
cat > template.html << 'EOF'
<h1>{{ title }}</h1>
<p>Welcome, {{ user.name }}!</p>

@if(user.admin) {
    <p>Admin tools available</p>
}

@for(item in items) {
    <div>{{ item.name }}: {{ item.price|currency('USD') }}</div>
}
EOF

# 3. Render the template
python << 'PYTHON'
from eden_engine.runtime.engine import EdenTemplateEngine

engine = EdenTemplateEngine()
context = {
    'title': 'My Page',
    'user': {'name': 'Alice', 'admin': True},
    'items': [
        {'name': 'Item 1', 'price': 19.99},
        {'name': 'Item 2', 'price': 29.99},
    ]
}

result = engine.render_file('template.html', context)
print(result)
PYTHON
```

---

## Installation

### System Requirements

- **Python:** 3.7 or higher
- **OS:** Linux, macOS, Windows
- **Memory:** Minimum 512MB (1GB+ recommended)
- **Disk:** 50MB for installation

### Step-by-Step Installation

#### 1. Install Dependencies

```bash
# Using pip
pip install lark==0.12.10 simpleeval markupsafe

# Using requirements.txt
cat > requirements.txt << 'EOF'
lark==0.12.10
simpleeval>=0.9.9
markupsafe>=2.0.0
EOF

pip install -r requirements.txt
```

#### 2. Install Eden Engine

```bash
# Copy the eden_engine package to your project
cp -r eden_engine /your/project/path/

# Or add to Python path
export PYTHONPATH=/path/to/eden:$PYTHONPATH
```

#### 3. Verify Installation

```bash
python << 'EOF'
from eden_engine.runtime.engine import EdenTemplateEngine
print("✅ Eden Engine installed successfully")

engine = EdenTemplateEngine()
result = engine.render("{{ 'Hello, World'|upper }}", {})
print(f"✅ Test render: {result}")
EOF
```

---

## Configuration

### Environment Setup

```python
# config.py
import os
from eden_engine.caching.cache import LRUCache, LFUCache, TTLCache
from eden_engine.performance import get_performance_manager

# Cache configuration
CACHE_STRATEGY = os.getenv('CACHE_STRATEGY', 'lru')
CACHE_SIZE = int(os.getenv('CACHE_SIZE', '1000'))
CACHE_TTL = int(os.getenv('CACHE_TTL', '3600'))

# Performance profiling
ENABLE_PROFILING = os.getenv('ENABLE_PROFILING', 'False').lower() == 'true'

# Security
ENABLE_SECURITY_AUDIT = os.getenv('ENABLE_SECURITY_AUDIT', 'True').lower() == 'true'

# Template paths
TEMPLATE_DIRS = [
    './templates',
    './custom_templates',
]

def get_cache():
    """Get configured cache instance."""
    if CACHE_STRATEGY == 'lru':
        return LRUCache(max_size=CACHE_SIZE)
    elif CACHE_STRATEGY == 'lfu':
        return LFUCache(max_size=CACHE_SIZE)
    elif CACHE_STRATEGY == 'ttl':
        return TTLCache(ttl_seconds=CACHE_TTL)
    else:
        return None  # No caching

def get_profiler():
    """Get performance profiler."""
    from eden_engine.performance import get_performance_manager
    manager = get_performance_manager()
    manager.profiler.enabled = ENABLE_PROFILING
    return manager
```

### Production Settings

```bash
# .env.production
CACHE_STRATEGY=lfu
CACHE_SIZE=5000
CACHE_TTL=7200
ENABLE_PROFILING=False
ENABLE_SECURITY_AUDIT=True
DEBUG=False
```

### Development Settings

```bash
# .env.development
CACHE_STRATEGY=none
CACHE_SIZE=100
CACHE_TTL=300
ENABLE_PROFILING=True
ENABLE_SECURITY_AUDIT=True
DEBUG=True
```

---

## Integration

### Django Integration

```python
# django_settings.py
INSTALLED_APPS = [
    # ...
    'eden_templates',
]

TEMPLATES = [{
    'BACKEND': 'eden_templates.backend.EdenTemplateBackend',
    'DIRS': ['templates/'],
    'OPTIONS': {
        'context_processors': [
            'django.template.context_processors.debug',
            'django.template.context_processors.request',
        ],
        'cache_strategy': 'lfu',
        'cache_size': 5000,
    },
}]

# Usage in views
from django.shortcuts import render

def my_view(request):
    context = {
        'title': 'My Page',
        'user': request.user,
    }
    return render(request, 'my_template.html', context)
```

### Flask Integration

```python
# app.py
from flask import Flask, render_template
from eden_engine.runtime.engine import EdenTemplateEngine
from eden_engine.caching.cache import LFUCache

app = Flask(__name__)

# Initialize Eden engine
engine = EdenTemplateEngine(cache=LFUCache(max_size=5000))

@app.route('/')
def index():
    context = {
        'title': 'Welcome',
        'items': [...],
    }
    html = engine.render_file('templates/index.html', context)
    return html

if __name__ == '__main__':
    app.run(debug=False)
```

### FastAPI Integration

```python
# main.py
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from eden_engine.runtime.engine import EdenTemplateEngine
from eden_engine.caching.cache import LFUCache

app = FastAPI()
engine = EdenTemplateEngine(cache=LFUCache(max_size=5000))

@app.get("/", response_class=HTMLResponse)
async def index():
    context = {
        'title': 'Welcome',
        'message': 'Hello, World!',
    }
    return engine.render_file('templates/index.html', context)
```

### Standalone Usage

```python
# standalone.py
from eden_engine.runtime.engine import EdenTemplateEngine
from eden_engine.caching.cache import LFUCache
from eden_engine.performance import get_performance_manager

# Initialize
engine = EdenTemplateEngine(cache=LFUCache(max_size=5000))
profiler = get_performance_manager()

# Render template
context = {
    'name': 'Alice',
    'items': [1, 2, 3],
}

with profiler.profile_operation('render'):
    result = engine.render_file('template.html', context)

print(result)
```

---

## Performance Tuning

### Cache Strategy Selection

| Strategy | Use Case | Memory | Speed |
|----------|----------|--------|-------|
| **LRU** | General web apps | Fixed | ⚡⚡ |
| **LFU** | Popular templates | Fixed | ⚡⚡⚡ |
| **TTL** | Frequently updated | Fixed | ⚡⚡ |
| **None** | Dynamic templates | Min | ⚡ |

### Recommended Settings by Load

```python
# Low traffic (< 100 requests/min)
cache = LRUCache(max_size=500)
profiling_enabled = True

# Medium traffic (100-1000 requests/min)
cache = LFUCache(max_size=2000)
profiling_enabled = False

# High traffic (> 1000 requests/min)
cache = LFUCache(max_size=10000)
profiling_enabled = False

# Critical system (mission-critical)
cache = LFUCache(max_size=20000)
profiling_enabled = False
# Add external caching: Redis, Memcached
```

### Performance Baseline

```python
from eden_engine.performance import run_benchmarks

# Establish baseline on your infrastructure
results = run_benchmarks()
print(results['report'])

# Save baseline for regression testing
with open('baseline.json', 'w') as f:
    json.dump(results['results'], f)
```

### Optimization Techniques

```python
# 1. Pre-compile frequently used templates
engine = EdenTemplateEngine(cache=LFUCache(max_size=5000))
common_templates = [
    'layout.html',
    'header.html',
    'footer.html',
]
for template_name in common_templates:
    engine.load_and_compile(template_name)

# 2. Use filter caching for expensive operations
# Apply filters to small subsets where possible

# 3. Avoid deeply nested templates
# Limit inheritance depth to 3-4 levels

# 4. Monitor with profiling
from eden_engine.performance import get_performance_report
report = get_performance_report()
print(report)
```

---

## Security Setup

### Input Validation

```python
from eden_engine.security import verify_component

# Verify security components at startup
verify_component('input_validation')
verify_component('injection_prevention')
verify_component('safe_evaluation')

# Run full audit
from eden_engine.security import run_security_audit
result = run_security_audit()
if not result.passed():
    raise Exception("Security audit failed!")
```

### Safe Context Building

```python
def build_safe_context(user, data):
    """Build template context with security checks."""
    return {
        'user': {
            'id': user.id,
            'name': user.name,
            'email': user.email,
            # Never include: password, tokens, secrets
        },
        'data': data,
        'timestamp': datetime.now().isoformat(),
        # Whitelist all context variables
    }
```

### Escaping Configuration

```python
# Automatic escaping is enabled by default
from markupsafe import Markup

# If you need to mark content as safe:
html_content = Markup('<b>Bold Text</b>')

# In templates:
# {{ user_input }}           # Auto-escaped
# {{ safe_html|safe }}       # Marked safe (use carefully!)
```

### Security Audit Scheduling

```python
import schedule
from eden_engine.security import get_security_summary

def daily_security_check():
    """Run daily security audit."""
    summary = get_security_summary()
    
    if "CRITICAL" in summary or "HIGH" in summary:
        send_alert(f"Security issue found:\n{summary}")
    else:
        log_info(f"Daily security check passed")

schedule.every().day.at("02:00").do(daily_security_check)
```

---

## Monitoring

### Health Check

```python
def health_check():
    """Health check endpoint for monitoring."""
    from eden_engine.runtime.engine import EdenTemplateEngine
    
    try:
        engine = EdenTemplateEngine()
        result = engine.render("{{ 1 + 1 }}", {})
        
        if result == "2":
            return {"status": "healthy", "engine": "ready"}
        else:
            return {"status": "degraded", "error": "render_failed"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
```

### Performance Monitoring

```python
from eden_engine.performance import get_performance_manager
import time

def monitor_performance():
    """Monitor performance metrics."""
    manager = get_performance_manager()
    report = manager.generate_performance_report()
    
    # Log metrics
    metrics = {
        'timestamp': time.time(),
        'avg_render_time': report.summary().get('avg_time_ms'),
        'throughput': report.summary().get('throughput_ops_sec'),
        'cache_hits': report.summary().get('cache_hit_rate'),
    }
    
    # Send to monitoring service
    logging_service.log_metrics(metrics)
```

### Alerting

```python
import logging

def setup_monitoring(alert_threshold_ms=50):
    """Setup performance alerts."""
    from eden_engine.performance import get_performance_manager
    
    manager = get_performance_manager()
    
    def check_performance():
        report = manager.generate_performance_report()
        avg_time = report.summary().get('avg_time_ms', 0)
        
        if avg_time > alert_threshold_ms:
            logging.warning(
                f"Performance degradation: {avg_time}ms > {alert_threshold_ms}ms"
            )
    
    # Check every 5 minutes
    schedule.every(5).minutes.do(check_performance)
```

---

## Troubleshooting

### Common Issues

#### Issue: Template not found
```python
# Solution: Check template paths
from eden_engine.caching.loaders import FileSystemLoader

loader = FileSystemLoader(['./templates', './custom_templates'])
try:
    template = loader.load('template.html')
except FileNotFoundError:
    print("Add template directory to search path")
```

#### Issue: Slow rendering
```python
# Solution: Enable profiling to find bottleneck
from eden_engine.performance import get_bottleneck_report

report = get_bottleneck_report()
print(report)  # Identifies which operations are slow
```

#### Issue: Memory leak
```python
# Solution: Check cache configuration
from eden_engine.caching.cache import LRUCache

# Don't use unlimited cache
cache = LRUCache(max_size=1000)  # Set reasonable limit

# Monitor memory usage
import tracemalloc
tracemalloc.start()
# ... render templates ...
current, peak = tracemalloc.get_traced_memory()
print(f"Current: {current / 1024 / 1024}MB; Peak: {peak / 1024 / 1024}MB")
```

#### Issue: Security warnings
```python
# Solution: Run security audit
from eden_engine.security import run_security_audit

result = run_security_audit()
for finding in result.findings:
    if finding.level.value in ['critical', 'high']:
        print(f"⚠️  {finding}")
```

### Debug Mode

```python
# Enable debugging
import logging

logging.basicConfig(level=logging.DEBUG)

# Get detailed error information
try:
    engine.render_file('template.html', context)
except Exception as e:
    logging.debug(f"Full traceback:", exc_info=True)
```

---

## Production Deployment Checklist

- ✅ Dependencies installed (`pip install -r requirements.txt`)
- ✅ Environment configured (`.env.production` created)
- ✅ Cache strategy selected (LFU recommended for production)
- ✅ Security audit passed (`run_security_audit()`)
- ✅ Performance baseline established (`run_benchmarks()`)
- ✅ Monitoring configured (health checks, alerts)
- ✅ Error handling robust (try/catch, logging)
- ✅ Templates optimized (inheritance depth ≤ 4)
- ✅ Escaping enabled (auto-escaping by default)
- ✅ Load testing completed (meets performance targets)

---

## Support & Resources

- **GitHub Issues:** Report bugs and request features
- **Documentation:** See PROJECT_COMPLETE.md for full API reference
- **Performance Guide:** See PHASE_4_OPTIMIZATION_COMPLETE.md
- **Security Guide:** See PHASE_5_SECURITY_COMPLETE.md
- **Examples:** See `/examples` directory

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | Mar 13, 2026 | Initial production release |

---

**Status:** Production Ready ✅  
**Last Updated:** March 13, 2026
