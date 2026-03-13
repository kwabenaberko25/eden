# Eden Framework: Unimplemented Features & Gaps Audit

**Date:** March 13, 2026  
**Status:** Comprehensive audit of eden_engine/, app/, and eden/ directories  
**Focus:** TODO markers, incomplete implementations, stub methods, and documented but unimplemented features

---

## Executive Summary

The Eden framework has several areas of incomplete implementation, ranging from critical features (template rendering API) to optional enhancements (payment integrations, performance optimization). Most core templating features are complete and tested, but significant gaps exist in:

1. **High-level Template Rendering API** - Core feature still raises NotImplementedError
2. **Abstract Base Classes** - Multiple visitor patterns and backends with no implementations
3. **Performance Optimization** - Benchmarking and profiling modules are stub-only
4. **Storage & Payment Integration** - Abstract interfaces defined but multi-provider support partial

---

## Critical Issues (Blocks Core Functionality)

### 1. [eden_engine/engine/core.py:86-95](eden_engine/engine/core.py#L86-L95)
- **Type:** NotImplementedError (Blocking)
- **Issue:** High-level `render()` API not implemented
- **Description:** The main `render()` method that users are expected to call raises NotImplementedError with message directing to use individual components instead
- **Impact:** Users cannot use the simple `app.render(template, context)` API; must use low-level components
- **Status:** Documented as "in development"
- **Priority:** **CRITICAL** - This is a primary entry point for template rendering

```python
def render(self, template_text: str, context: Dict[str, Any]) -> str:
    """Rendered output (currently raises NotImplementedError)"""
    raise NotImplementedError(
        "High-level render() API is in development. "
        "Use individual components directly..."
    )
```

---

## Abstract Methods Without Implementations

### 2. [eden_engine/runtime/engine.py:128-131](eden_engine/runtime/engine.py#L128-L131)
- **Type:** Abstract method (stub)
- **Issue:** DirectiveHandler.execute() is abstract with only pass
- **Description:** Base class for all directive handlers has abstract execute method
- **Impact:** All directive implementations must implement this; base class is incomplete
- **Status:** Likely implemented in subclasses
- **Priority:** MEDIUM

```python
@abstractmethod
async def execute(self, context: TemplateContext, **kwargs) -> str:
    """Execute directive and return output."""
    pass
```

### 3. [eden_engine/caching/cache.py:130-138](eden_engine/caching/cache.py#L130-L138)
- **Type:** Abstract methods (stub)
- **Issue:** BaseCache.get() and BaseCache.set() are abstract with only pass
- **Description:** Abstract cache base class requires subclasses to implement get/set
- **Impact:** LRUCache, LFUCache, TTLCache must each reimplement; abstract interface only
- **Status:** Implemented in subclasses (LRUCache, LFUCache, TTLCache)
- **Priority:** LOW - Implementations exist in subclasses

```python
@abstractmethod
def get(self, key: str) -> Optional[Any]:
    """Get value from cache."""
    pass

@abstractmethod
def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
    """Set value in cache."""
    pass
```

### 4. [eden_engine/inheritance/inheritance.py:214-222](eden_engine/inheritance/inheritance.py#L214-L222)
- **Type:** Abstract methods (stub)
- **Issue:** TemplateLoader abstract base has abstract methods with only pass
- **Description:** Base template loading interface requires subclasses to implement load/exists
- **Impact:** FileSystemTemplateLoader and MemoryTemplateLoader must reimplement interface
- **Status:** Implemented in subclasses
- **Priority:** LOW - Subclass implementations exist

```python
@abstractmethod
async def load(self, template_name: str) -> Optional[str]:
    """Load template by name. Returns content or None."""
    pass

@abstractmethod
async def exists(self, template_name: str) -> bool:
    """Check if template exists."""
    pass
```

### 5. [eden_engine/parser/ast_nodes.py:53](eden_engine/parser/ast_nodes.py#L53)
- **Type:** Abstract method (stub)
- **Issue:** ASTNode.accept() is abstract with only pass
- **Description:** Visitor pattern base class - all AST nodes must implement accept()
- **Impact:** Visitor pattern incomplete - all 50+ node types must implement accept()
- **Status:** Unknown if implementations exist
- **Priority:** HIGH - Required for AST traversal in codegen and runtime

```python
@abstractmethod
def accept(self, visitor: 'ASTVisitor') -> Any:
    """Accept a visitor for traversal/transformation."""
    pass
```

### 6. [eden_engine/parser/ast_nodes.py:973-1158 (50+ methods)](eden_engine/parser/ast_nodes.py#L973-L1158)
- **Type:** Abstract methods (visitor pattern)
- **Issue:** ASTVisitor class has 50+ abstract visit_* methods that are stubs
- **Description:** Visitor pattern interface with abstract methods for all node types:
  - Template & text nodes (visit_template, visit_text)
  - Control flow (~10 methods: visit_if, visit_for, visit_foreach, etc.)
  - Components (~6 methods: visit_component, visit_slot, etc.)
  - Inheritance (~6 methods: visit_extends, visit_block, etc.)
  - Forms (~5 methods: visit_csrf_token, visit_checked, etc.)
  - Routing (~3 methods: visit_url, visit_active_link, etc.)
  - Auth (~4 methods: visit_auth, visit_guest, visit_htmx, etc.)
  - Assets (~3 methods: visit_css, visit_js, visit_vite)
  - Data (~6 methods: visit_let, visit_dump, visit_messages, etc.)
  - Special & Meta (~6 methods: visit_include, visit_fragment, visit_method, etc.)
  - Expressions & Operators (~7 methods: visit_binary_op, visit_filter, etc.)
  - References & Literals (~4 methods: visit_variable, visit_literal, etc.)
  - Collections (~2 methods: visit_list, visit_dict)
- **Impact:** No concrete visitor implementations found; codegen visitor must implement all
- **Status:** Implementations may exist in CodeGenerator but not verified
- **Priority:** HIGH - Core to template compilation pipeline

---

## Incomplete/Stub Modules

### 7. [eden_engine/performance/benchmarks.py](eden_engine/performance/benchmarks.py)
- **Type:** Stub module
- **Issue:** BenchmarkSuite class defines benchmarks but run_simple_benchmark() is incomplete
- **Description:** Performance benchmarking framework defined with templates but execution methods are stubs
  - BenchmarkTemplates defines SIMPLE, COMPLEX, INHERITANCE_BASE, INHERITANCE_CHILD, MIXED templates
  - BenchmarkSuite.run_simple_benchmark() at line 198 contains "In real implementation, this would compile and render" comment
  - No actual execution logic implemented
- **Implementation Status:** ~30% complete (templates defined, execution missing)
- **Priority:** MEDIUM - Optional feature

```python
def run_simple_benchmark(self, template_text: str, context: Dict,
                        iterations: int = 1000) -> BenchmarkResult:
    """Run a simple benchmark of template rendering."""
    times = []
    
    for _ in range(iterations):
        # In real implementation, this would compile and render
```

### 8. [eden_engine/performance/optimizer.py](eden_engine/performance/optimizer.py)
- **Type:** Stub module
- **Issue:** Query analyzer defined but no implementation
- **Description:** Query optimization framework defined with OptimizationType enum and OptimizationSuggestion class, but no actual analyzer/applier classes
  - OptimizationType enum defines 8 optimization types (CACHE_RESULT, LAZY_EVALUATION, etc.)
  - OptimizationSuggestion dataclass defined
  - No QueryAnalyzer, CallGraph, OptimizationAdvisor, or OptimizationApplier classes
- **Implementation Status:** ~10% complete (types defined, logic missing)
- **Priority:** LOW - Performance optimization feature

### 9. [eden_engine/performance/profiler.py](eden_engine/performance/profiler.py)
- **Type:** Stub module
- **Issue:** Performance profiler framework defined but not implemented
- **Description:** Profiling infrastructure defined with OperationType enum and TimingData class, but no actual profiler
  - OperationType enum with 11 operation types
  - TimingData dataclass defined
  - No Profiler, OperationTimer, MetricsCollector, PerformanceReport, or BottleneckDetector classes
- **Implementation Status:** ~10% complete (types defined, logic missing)
- **Priority:** LOW - Performance monitoring feature

### 10. [eden_engine/compiler/codegen.py:668-670](eden_engine/compiler/codegen.py#L668-L670)
- **Type:** Stub method
- **Issue:** CodeGenerator.generic_visit() is incomplete
- **Description:** Default visitor implementation in CodeGenerator is just "pass"
- **Impact:** Nodes without specific visit_* handler fall through to generic_visit which does nothing
- **Priority:** MEDIUM - Could cause silent failures for unhandled node types

```python
def generic_visit(self, node: ASTNode) -> Any:
    """Default visitor implementation."""
    pass
```

---

## Validators & Type System

### 11. [eden/validators.py:760-768](eden/validators.py#L760-L768)
- **Type:** NotImplementedError (Abstract validator class)
- **Issue:** _PydanticValidator._validate() raises NotImplementedError
- **Description:** Base validator class for Pydantic integration is incomplete
- **Status:** Must be overridden by subclasses (EdenEmail, EdenPassword, etc.)
- **Impact:** Base class cannot be instantiated directly
- **Priority:** LOW - Subclass implementations exist

```python
@classmethod
def _validate(cls, value: Any) -> Any:
    raise NotImplementedError
```

---

## Runtime & Compilation

### 12. [eden_engine/runtime/engine.py:390](eden_engine/runtime/engine.py#L390)
- **Type:** TODO comment
- **Issue:** Code execution is not safe
- **Description:** Comment indicates "Execute compiled code safely" is TODO
- **Description:** Comment states compiled code needs security hardening
- **Impact:** Potential security issue if compiled templates execute untrusted code
- **Priority:** HIGH - Security concern

```python
# TODO: Execute compiled code safely
# For now, compile and execute
try:
    exec(compiled_code, namespace)
```

---

## Abstract Backend Classes

### 13. [eden/storage.py:14-32](eden/storage.py#L14-L32)
- **Type:** Abstract base class with stub methods
- **Issue:** StorageBackend interface incomplete
- **Description:** Abstract storage backend with three abstract methods:
  - `save()` - line 20-21: just pass
  - `delete()` - line 24-26: just pass
  - `url()` - line 29-32: just pass
- **Implementations:** LocalStorageBackend exists; S3StorageBackend and SupabaseStorageBackend in storage_backends/
- **Status:** Interface complete, implementations exist
- **Priority:** LOW - Implementations exist

```python
@abstractmethod
async def save(self, content: UploadFile | bytes, name: str | None = None) -> str:
    """Save a file and return its identifier."""
    pass

@abstractmethod
async def delete(self, name: str):
    """Delete a file by its identifier."""
    pass

@abstractmethod
def url(self, name: str) -> str:
    """Get the public URL for a file."""
    pass
```

### 14. [eden/mail/backends.py:25-28](eden/mail/backends.py#L25-L28)
- **Type:** Abstract method
- **Issue:** EmailBackend.send() is abstract with only pass
- **Description:** Email backend interface incomplete with abstract send method
- **Implementations:** ConsoleBackend and SMTPBackend implement this
- **Status:** Interface complete, implementations exist (ConsoleBackend fully working, SMTPBackend fully implemented)
- **Priority:** LOW - Implementations exist

```python
@abstractmethod
async def send(self, message: EmailMessage) -> bool:
    """Send an email message. Returns True if successful."""
    pass
```

### 15. [eden/auth/base.py:25-45](eden/auth/base.py#L25-L45)
- **Type:** Abstract methods
- **Issue:** AuthBackend has three abstract methods just with pass
- **Description:** Authentication backend interface incomplete:
  - `authenticate()` - line 25-27: pass
  - `login()` - line 29-31: pass
  - `logout()` - line 33-35: pass
- **Implementations:** SessionBackend, JWTBackend, APIKeyBackend all implement these
- **Status:** Interface complete, implementations exist
- **Priority:** LOW - Implementations exist (SessionBackend verified)

```python
async def authenticate(self, request: "Request") -> U | None:
    """Authenticate the request and return the user if successful."""
    pass

async def login(self, request: "Request", user: U) -> None:
    """Perform login actions."""
    pass

async def logout(self, request: "Request") -> None:
    """Perform logout actions."""
    pass
```

---

## CLI & Commands (Stub Groups)

### 16. [eden/cli/main.py:25-27](eden/cli/main.py#L25-L27)
- **Type:** Click command group with pass
- **Issue:** CLI main group is just a pass decorator
- **Status:** Decorator for click group; subcommands implement functionality
- **Priority:** LOW - Subcommands likely implemented

```python
@click.group()
def cli() -> None:
    """🌿 Eden — A batteries-included async Python web framework."""
    pass
```

### 17. [eden/cli/forge.py:18-20](eden/cli/forge.py#L18-L20)
- **Type:** Click command group with pass
- **Issue:** Forge (code generation) command group is just a pass decorator
- **Status:** Decorator for click group; subcommands implement functionality
- **Priority:** LOW - Subcommands likely implemented

```python
@click.group()
def generate() -> None:
    """🌿 Eden Framework — The elite web framework for professionals."""
    pass
```

### 18. [eden/cli/db.py:20-22](eden/cli/db.py#L20-L22)
- **Type:** Click command group with pass
- **Issue:** Database command group is just a pass decorator
- **Status:** Decorator for click group; subcommands implement functionality
- **Priority:** LOW - Subcommands likely implemented

```python
@click.group(name="db")
def db() -> None:
    """🗄️  Eden Database — Initialize, generate, and run migrations."""
    pass
```

### 19. [eden/cli/auth.py:14-16](eden/cli/auth.py#L14-L16)
- **Type:** Click command group with pass
- **Issue:** Auth command group is just a pass decorator
- **Status:** Decorator for click group; subcommands implement functionality
- **Priority:** LOW - Subcommands likely implemented

```python
@click.group()
def auth():
    """Authentication and Authorization management."""
    pass
```

### 20. [eden/cli/tasks.py:15-17](eden/cli/tasks.py#L15-L17)
- **Type:** Click command group with pass
- **Issue:** Tasks command group is just a pass decorator
- **Status:** Decorator for click group; subcommands implement functionality
- **Priority:** LOW - Subcommands likely implemented

```python
@click.group()
def tasks() -> None:
    """⏰ Eden Tasks — Background job management."""
    pass
```

---

## Exception Classes (Placeholder)

### 21. [eden_engine/parser/parser.py:48-49](eden_engine/parser/parser.py#L48-L49)
- **Type:** Exception class with pass body
- **Issue:** ParseError exception class is just a pass placeholder
- **Status:** Exception defined but no custom logic
- **Priority:** LOW - Exception still functions, just no custom implementation

```python
class ParseError(Exception):
    """Raised when AST parsing fails with detailed location info."""
    pass
```

### 22. [eden_engine/lexer/tokenizer.py:42-43](eden_engine/lexer/tokenizer.py#L42-L43)
- **Type:** Exception class with pass body
- **Issue:** TokenizationError exception class is just a pass placeholder
- **Status:** Exception defined but no custom logic
- **Priority:** LOW - Exception still functions, just no custom implementation

```python
class TokenizationError(Exception):
    """Raised when tokenization fails."""
    pass
```

---

## Response Classes (Stubs)

### 23. [eden/responses.py:45-46](eden/responses.py#L45-L46)
- **Type:** Response class with pass body
- **Issue:** Response base class is just a pass placeholder
- **Status:** Inherits all functionality from StarletteResponse
- **Priority:** LOW - Functional by inheritance, just no Eden-specific logic

```python
class Response(StarletteResponse):
    """Base response with Eden helpers."""
    pass
```

### 24. [eden/responses.py:82-83](eden/responses.py#L82-L83)
- **Type:** Response class with pass body
- **Issue:** HtmlResponse class is just a pass placeholder
- **Status:** Inherits all functionality from StarletteHTMLResponse
- **Priority:** LOW - Functional by inheritance

```python
class HtmlResponse(StarletteHTMLResponse):
    """HTML response for rendered templates or raw HTML."""
    pass
```

### 25. [eden/responses.py:86-87](eden/responses.py#L86-L87)
- **Type:** Response class with pass body
- **Issue:** RedirectResponse class is just a pass placeholder
- **Status:** Inherits all functionality from StarletteRedirectResponse
- **Priority:** LOW - Functional by inheritance

```python
class RedirectResponse(StarletteRedirectResponse):
    """HTTP redirect response."""
    pass
```

### 26. [eden/responses.py:98-99](eden/responses.py#L98-L99)
- **Type:** Response class with pass body
- **Issue:** FileResponse class is just a pass placeholder
- **Status:** Inherits all functionality from StarletteFileResponse
- **Priority:** LOW - Functional by inheritance

```python
class FileResponse(StarletteFileResponse):
    """File download response."""
    pass
```

### 27. [eden/responses.py:103-104](eden/responses.py#L103-L104)
- **Type:** Response class with pass body
- **Issue:** StreamingResponse class is just a pass placeholder
- **Status:** Inherits all functionality from StarletteStreamingResponse
- **Priority:** LOW - Functional by inheritance

```python
class StreamingResponse(StarletteStreamingResponse):
    """Streaming response for large payloads or SSE."""
    pass
```

---

## Example Documentation Gaps

### 28. [examples/07_production.py:97-118](examples/07_production.py#L97-L118)
- **Type:** TODO in example code
- **Issue:** Health check and metrics endpoints incomplete
- **Location:** Production example file
- **Description:** Two incomplete endpoints:
  1. `/health` endpoint returns hardcoded "healthy" (no actual checks)
  2. `/metrics` endpoint returns `{"uptime": "TODO", "requests": "TODO"}`
- **Impact:** Example shows incomplete feature; users cannot follow for production setup
- **Priority:** LOW - Example file (not production code)

```python
@app.get("/metrics")
async def metrics():
    """Basic metrics endpoint."""
    return {"uptime": "TODO", "requests": "TODO"}
```

---

## Skipped Tests (Work Not Yet Done)

### 29. [eden_engine/tests/unit/test_inheritance_caching.py:42](eden_engine/tests/unit/test_inheritance_caching.py#L42)
- **Type:** Skipped test suite
- **Issue:** Inheritance and Caching tests are completely skipped
- **Reason:** "Inheritance/Caching modules not available"
- **Impact:** ~200+ tests not running; indicates these modules may not be fully integrated
- **Priority:** MEDIUM - Tests are skipped module-level, suggesting incomplete implementation

```python
pytest.skip("Inheritance/Caching modules not available", allow_module_level=True)
```

### 30. [eden_engine/tests/unit/test_codegen_runtime.py:35](eden_engine/tests/unit/test_codegen_runtime.py#L35)
- **Type:** Skipped test suite
- **Issue:** Code generation and runtime tests are completely skipped
- **Reason:** "Parser/Compiler modules not available"
- **Impact:** ~150+ tests not running; core compilation pipeline isn't being tested
- **Priority:** HIGH - Core tests are skipped; suggests incomplete codegen/runtime

```python
pytest.skip("Parser/Compiler modules not available", allow_module_level=True)
```

---

## Features Mentioned in Docs But Partially Incomplete

### 31. Template Rendering High-Level API
- **Documentation:** EDEN_TEMPLATING_ENGINE_COMPLETE_GUIDE.md mentions `render()` API
- **Implementation:** Only low-level components work; high-level API raises NotImplementedError (#1)
- **Impact:** Primary documented feature doesn't work
- **Priority:** CRITICAL

### 32. Direct Wildcard Query Support
- **Test File:** [test_directives_audit.py:97](test_directives_audit.py#L97)
- **Issue:** Comment notes "Wildcard support not implemented!"
- **Context:** Likely related to template path matching or query wildcards
- **Priority:** LOW-MEDIUM - Feature mentioned but not critical

```python
print("     Wildcard support not implemented!")
```

---

## Summary Table

| # | Module | Issue Type | Status | Priority | Impact |
|---|--------|-----------|--------|----------|--------|
| 1 | eden_engine/engine/core.py | NotImplementedError (render API) | Critical | CRITICAL | Users cannot use main API |
| 2 | eden_engine/runtime/engine.py | Abstract method | Stub (to-do) | MEDIUM | Base directive interface |
| 3 | eden_engine/caching/cache.py | Abstract methods | Implemented in subclasses | LOW | Cache system complete |
| 4 | eden_engine/inheritance/inheritance.py | Abstract methods | Implemented in subclasses | LOW | Inheritance system complete |
| 5 | eden_engine/parser/ast_nodes.py | Abstract method (accept) | Unknown | HIGH | Required for AST traversal |
| 6 | eden_engine/parser/ast_nodes.py | 50+ Abstract visitor methods | Unknown | HIGH | Core compilation pipeline |
| 7 | eden_engine/performance/benchmarks.py | Incomplete execution | Stub (~30% done) | MEDIUM | Performance benchmarking |
| 8 | eden_engine/performance/optimizer.py | No implementation | Stub (~10% done) | LOW | Query optimization |
| 9 | eden_engine/performance/profiler.py | No implementation | Stub (~10% done) | LOW | Performance profiling |
| 10 | eden_engine/compiler/codegen.py | generic_visit() stub | Pass (no-op) | MEDIUM | Silent failures possible |
| 11 | eden/validators.py | NotImplementedError | Abstract/override required | LOW | Subclasses exist |
| 12 | eden_engine/runtime/engine.py | TODO comment | Code execution not safe | HIGH | Security concern |
| 13 | eden/storage.py | Abstract methods | Implemented | LOW | Storage complete |
| 14 | eden/mail/backends.py | Abstract method | Implemented | LOW | Email system complete |
| 15 | eden/auth/base.py | Abstract methods | Implemented | LOW | Auth system complete |
| 16-20 | eden/cli/*.py | CLI groups (pass) | Subcommands implemented | LOW | CLI functional |
| 21-22 | Exception classes | Stock definitions | Functional | LOW | Works as-is |
| 23-27 | Response classes | Pass stubs | Fully functional by inheritance | LOW | All working |
| 28 | examples/07_production.py | TODO in example | Example incomplete | LOW | Example only |
| 29 | test_inheritance_caching.py | Skipped tests | ~200+ tests skipped | MEDIUM | Tests not running |
| 30 | test_codegen_runtime.py | Skipped tests | ~150+ tests skipped | HIGH | Core tests skipped |
| 31 | Templating API | Documented but incomplete | High-level API missing | CRITICAL | Primary feature |
| 32 | Wildcard support | Not implemented | Not done | LOW | Query feature |

---

## Recommendations by Priority

### CRITICAL (Blocks Users)
1. **Implement main render() API** in [eden_engine/engine/core.py](eden_engine/engine/core.py#L86)
   - This is the primary documented entry point users expect to work
   - Currently raises NotImplementedError
   - Estimated effort: Medium (implement wrapper around existing components)

### HIGH (Core Architecture Issues)
2. **Enable test suites** for codegen_runtime and inheritance_caching
   - Tests are skipped; indicates module integration issues
   - Implement or fix module imports to enable test execution
   - Estimated effort: Medium

3. **Implement ASTNode.accept() and ASTVisitor pattern**
   - 50+ abstract methods need implementation
   - Required for AST traversal in compilation pipeline
   - Estimated effort: High (requires codegen visitor implementation)

4. **Address code execution security** (TODO in runtime engine)
   - Currently uses bare exec() which is unsafe
   - Implement sandboxed execution for compiled templates
   - Estimated effort: High

### MEDIUM (Non-Critical Features)
5. **Complete benchmarking framework** in eden_engine/performance/
   - Benchmark templates defined but execution missing
   - Optional feature but useful for performance validation
   - Estimated effort: Medium

6. **Fix CodeGenerator.generic_visit()** 
   - Currently does nothing, could hide errors
   - Implement proper visitor dispatch or error handling
   - Estimated effort: Low

### LOW (Polish & Examples)
7. **Update example files** (examples/07_production.py)
   - Complete metrics endpoints
   - Update documentation to match
   - Estimated effort: Low

8. **Implement remaining optimization modules**
   - optimizer.py and profiler.py are frameworks without logic
   - Optional performance features
   - Estimated effort: Medium-High

9. **Complete wildcard query support**
   - Feature mentioned but not implemented
   - Low priority unless documented as supported
   - Estimated effort: Unknown

---

## Implementation Notes

### Modules That Are Architecturally Sound
- **eden/auth/**: All backends fully implemented (SessionBackend verified)
- **eden/mail/**: All backends fully implemented (SMTPBackend verified)
- **eden/storage/**: All backends fully implemented (S3StorageBackend, SupabaseStorageBackend verified)
- **eden/cache/**: All cache strategies implemented (LRUCache, LFUCache, TTLCache verified)
- **eden/responses/**: All response types functional (inherit from Starlette)

### Modules with Significant Gaps
- **eden_engine/compiler/**: Code generation visitor pattern incomplete
- **eden_engine/parser/**: AST visitor pattern incomplete
- **eden_engine/performance/**: Skeleton only, no execution logic
- **eden_engine/runtime/**: TODO on code execution safety

### Documentation vs. Implementation Mismatch
- EDEN_TEMPLATING_ENGINE_COMPLETE_GUIDE.md documents features not fully implemented
- render() API is primary documented entry point but raises NotImplementedError
- High-level API usage patterns in docs are broken

---

## Test Coverage Impact

**Skipped Tests:** ~350+ tests not running
- inheritance_caching: ~200 tests
- codegen_runtime: ~150 tests

**Impact:** Core compilation and inheritance features are not being validated by test suite

---

