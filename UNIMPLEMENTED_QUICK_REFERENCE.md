# Eden Framework: Unimplemented Features Quick Reference

**Updated:** March 13, 2026  
**Focus:** Critical gaps and blockers organized by severity

---

## 🔴 CRITICAL (Blocks Users Immediately)

### 1. Template Rendering API - NotImplementedError
- **File:** [eden_engine/engine/core.py:86](eden_engine/engine/core.py#L86)
- **Issue:** Main `render()` method raises NotImplementedError
- **Impact:** Users cannot use documented high-level API
- **Status:** Directs users to use undocumented low-level components instead
- **Fix Required:** YES - Implement wrapper around existing components

### 2. Code Execution Is Unsafe
- **File:** [eden_engine/runtime/engine.py:390](eden_engine/runtime/engine.py#L390)
- **Issue:** Uses bare `exec()` for compiled template code
- **Security Risk:** Potential injection/sandbox bypass
- **Comment:** "TODO: Execute compiled code safely"
- **Fix Required:** YES - Implement sandboxed execution

---

## 🟠 HIGH (Core Architecture)

### 3. Test Suites Are Skipped
- **Files:**
  - [eden_engine/tests/unit/test_codegen_runtime.py:35](eden_engine/tests/unit/test_codegen_runtime.py#L35) - 150+ tests skipped
  - [eden_engine/tests/unit/test_inheritance_caching.py:42](eden_engine/tests/unit/test_inheritance_caching.py#L42) - 200+ tests skipped
- **Reason:** Parser/Compiler modules reported "not available"
- **Impact:** Core compilation pipeline not being tested
- **Fix Required:** YES - Fix module imports or complete implementations

### 4. AST Visitor Pattern Incomplete
- **File:** [eden_engine/parser/ast_nodes.py:973-1158](eden_engine/parser/ast_nodes.py#L973-L1158)
- **Scope:** 50+ abstract `visit_*()` methods with just `pass`
- **Impact:** No concrete visitor for AST traversal/codegen
- **Categories:**
  - Template/text (2 methods)
  - Control flow (10 methods)
  - Components (6 methods)
  - Inheritance (6 methods)
  - Forms (5 methods)
  - Routing (3 methods)
  - Auth (4 methods)
  - Assets (3 methods)
  - Data (6 methods)
  - Special/Meta (6 methods)
  - Expressions (7 methods)
  - References & Literals (4 methods)
  - Collections (2 methods)
- **Fix Required:** YES - Implement CodeGenerator visitor or alternative traversal

### 5. ASTNode.accept() Not Implemented
- **File:** [eden_engine/parser/ast_nodes.py:53-61](eden_engine/parser/ast_nodes.py#L53-L61)
- **Issue:** Abstract `accept()` method just has `pass`
- **Impact:** Visitor pattern incomplete; affects all 50+ node types
- **Fix Required:** YES - Implement in all AST node classes

---

## 🟡 MEDIUM (Important Features Partially Done)

### 6. Performance Benchmarking
- **File:** [eden_engine/performance/benchmarks.py](eden_engine/performance/benchmarks.py)
- **Status:** ~30% done - Templates defined, execution missing
- **Notes:** Contains comment "In real implementation, this would compile and render"
- **Fix Required:** YES - Implement benchmark execution

### 7. CodeGenerator.generic_visit()
- **File:** [eden_engine/compiler/codegen.py:668-670](eden_engine/compiler/codegen.py#L668-L670)
- **Issue:** Default visitor is just `pass` (no-op)
- **Risk:** Unhandled AST nodes silently fail
- **Fix Required:** YES - Implement error handling or visitor dispatch

### 8. Performance & Profiling Modules Are Empty
- **Files:**
  - [eden_engine/performance/optimizer.py](eden_engine/performance/optimizer.py) - ~10% done
  - [eden_engine/performance/profiler.py](eden_engine/performance/profiler.py) - ~10% done
- **Status:** Only type definitions, no actual logic
- **Priority:** Lower (optional feature)
- **Fix Required:** NO (optional enhancement)

### 9. Directive Execution Base Class
- **File:** [eden_engine/runtime/engine.py:128-131](eden_engine/runtime/engine.py#L128-L131)
- **Issue:** DirectiveHandler.execute() is abstract with just `pass`
- **Status:** Implemented in subclasses
- **Fix Required:** MAYBE (verify subclass implementations)

---

## 🟢 LOW (Non-Critical or Already Handled)

### 10. Abstract Base Classes (Working by Inheritance)
These are complete via subclass implementations:
- **Storage:** [eden/storage.py](eden/storage.py) ✅ Implemented in storage_backends/
- **Mail:** [eden/mail/backends.py](eden/mail/backends.py) ✅ ConsoleBackend, SMTPBackend work
- **Auth:** [eden/auth/base.py](eden/auth/base.py) ✅ SessionBackend, JWTBackend, APIKeyBackend work
- **Caching:** [eden_engine/caching/cache.py](eden_engine/caching/cache.py) ✅ LRUCache, LFUCache, TTLCache implemented
- **Template Loading:** [eden_engine/inheritance/inheritance.py](eden_engine/inheritance/inheritance.py) ✅ FileSystemTemplateLoader, MemoryTemplateLoader

### 11. CLI Command Groups
- **Files:** eden/cli/main.py, forge.py, db.py, auth.py, tasks.py
- **Issue:** Groups are just decorators with `pass`
- **Status:** Functional by design (Starlette Click pattern)
- **Note:** Subcommands implement functionality

### 12. Response Classes
- **File:** [eden/responses.py](eden/responses.py)
- **Issue:** Response, HtmlResponse, FileResponse, StreamingResponse are stubs
- **Status:** Fully functional via Starlette inheritance
- **Note:** No Eden-specific logic needed

### 13. Exception Classes
- **Files:** eden_engine/parser/parser.py, eden_engine/lexer/tokenizer.py
- **Issue:** ParseError, TokenizationError are empty classes
- **Status:** Functional as-is (can still raise/catch)
- **Note:** No custom logic needed

### 14. Example Code
- **File:** [examples/07_production.py](examples/07_production.py#L113)
- **Issue:** Metrics endpoint has TODO ("uptime": "TODO", "requests": "TODO")
- **Status:** Example file (not production code)
- **Note:** Low priority

### 15. Validators
- **File:** [eden/validators.py:766](eden/validators.py#L766)
- **Issue:** _PydanticValidator._validate() raises NotImplementedError
- **Status:** Must be overridden by subclasses
- **Note:** By design (abstract base)

---

## Priority-Based Fix Order

### Phase 1: CRITICAL (Do First)
1. Implement `render()` API in engine/core.py
2. Fix code execution security in runtime/engine.py
3. Enable/fix test suites

### Phase 2: HIGH (Do Next)
4. Implement or fix AST visitor pattern (codegen)
5. Implement ASTNode.accept() across all node types

### Phase 3: MEDIUM (Nice to Have)
6. Complete benchmarking framework
7. Fix generic_visit() to handle edge cases
8. Complete optimizer and profiler modules

### Phase 4: LOW (Polish)
9. Update example code
10. Add missing docstrings

---

## Files Needing Changes

### Must Fix
- [ ] eden_engine/engine/core.py (render API)
- [ ] eden_engine/runtime/engine.py (safe execution + generic_visit)
- [ ] eden_engine/parser/ast_nodes.py (visitor pattern + accept)
- [ ] eden_engine/compiler/codegen.py (visitor implementation)
- [ ] eden_engine/tests/unit/test_codegen_runtime.py (enable tests)
- [ ] eden_engine/tests/unit/test_inheritance_caching.py (enable tests)

### Should Fix
- [ ] eden_engine/performance/benchmarks.py (complete execution)
- [ ] eden_engine/runtime/engine.py (DirectiveHandler verification)

### Could Fix (Optional)
- [ ] eden_engine/performance/optimizer.py (implement logic)
- [ ] eden_engine/performance/profiler.py (implement logic)
- [ ] examples/07_production.py (complete metrics)

---

## Verified Complete (No Action Needed)

✅ Storage system (all backends)  
✅ Email system (all backends)  
✅ Authentication system (all backends)  
✅ Caching system (all strategies)  
✅ Template loading & inheritance  
✅ CLI system  
✅ Response types  
✅ Request handling  
✅ Middleware system  

---

## Testing Status

| Component | Tests | Status |
|-----------|-------|--------|
| Codegen & Runtime | ~150 | 🔴 SKIPPED |
| Inheritance & Caching | ~200 | 🔴 SKIPPED |
| Other systems | Many | 🟢 Running |

**Total Skipped:** ~350+ tests

---

