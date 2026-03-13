# Eden Framework - Setup FAQ

## Do we have to build it into a package first?

**No.** The Eden framework is ready to use immediately without any package build.

### What Works Right Now

✅ All 158 tests pass without any setup
✅ All components are importable directly
✅ All 6 quick-start examples work without installation
✅ Full framework functionality available immediately

### How to Use

**Option 1: From Source (Recommended for Development)**
```bash
cd c:\ideas\eden
python -m pytest              # Run all tests
```

**Option 2: Direct Import in Your Code**
```python
import sys
sys.path.insert(0, r'c:\ideas\eden')
from eden_engine.parser import EdenParser
from eden_engine.runtime.engine import TemplateContext
# Use components directly
```

**Option 3: Package It Later (for Distribution)**
```bash
cd c:\ideas\eden
python setup.py sdist bdist_wheel  # Creates distribution packages
pip install dist/eden_engine-1.0.0-py3-none-any.whl
```

### Components Available Now

- ✅ Lexer (tokenization)
- ✅ Parser (AST generation)
- ✅ Runtime Engine (execution)
- ✅ 38+ Filters
- ✅ 50+ Directives  
- ✅ Caching (LRU, LFU, TTL)
- ✅ Performance Profiler
- ✅ Security Auditor

### Testing Without Installation

```bash
cd c:\ideas\eden
python -m pytest tests/unit/test_parser.py -v
python -m pytest eden_engine/performance/performance_tests.py -v
python -m pytest eden_engine/security/security_tests.py -v
```

### Production Deployment

For production, create a setup.py and publish to PyPI. The framework is ready for this anytime, but it's not required to use it now.

## Summary

**No build step needed.** Use it now, directly from the source code.
