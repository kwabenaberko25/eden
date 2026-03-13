# Eden Framework: Unimplemented Features by File

**Quick lookup table organized by file path**

---

## eden_engine/

### eden_engine/engine/core.py
| Line | Issue | Priority | Type |
|------|-------|----------|------|
| 86-95 | `render()` raises NotImplementedError | **CRITICAL** | NotImplementedError |

### eden_engine/runtime/engine.py
| Line | Issue | Priority | Type |
|------|-------|----------|------|
| 128-131 | `DirectiveHandler.execute()` - abstract with just `pass` | MEDIUM | Abstract method |
| 390 | "TODO: Execute compiled code safely" - security risk | **CRITICAL** | TODO comment |

### eden_engine/compiler/codegen.py
| Line | Issue | Priority | Type |
|------|-------|----------|------|
| 668-670 | `generic_visit()` - just `pass` (no-op for unhandled nodes) | MEDIUM | Incomplete method |

### eden_engine/parser/ast_nodes.py
| Line | Issue | Priority | Type |
|------|-------|----------|------|
| 53-61 | `ASTNode.accept()` - abstract with just `pass` | **HIGH** | Abstract method |
| 973-1158 | `ASTVisitor` - 50+ abstract `visit_*()` methods | **HIGH** | 50+ abstract methods |

### eden_engine/caching/cache.py
| Line | Issue | Priority | Type |
|------|-------|----------|------|
| 130-138 | `BaseCache.get()` and `.set()` - abstract methods | LOW | Abstract methods |

**Status:** ✅ Implemented in subclasses (LRUCache, LFUCache, TTLCache)

### eden_engine/inheritance/inheritance.py
| Line | Issue | Priority | Type |
|------|-------|----------|------|
| 214-222 | `TemplateLoader.load()` and `.exists()` - abstract methods | LOW | Abstract methods |

**Status:** ✅ Implemented in subclasses (FileSystemTemplateLoader, MemoryTemplateLoader)

### eden_engine/performance/benchmarks.py
| Line | Issue | Priority | Type |
|------|-------|----------|------|
| 198+ | `BenchmarkSuite.run_simple_benchmark()` - missing execution | MEDIUM | Incomplete implementation |
| Comment | "In real implementation, this would compile and render" | MEDIUM | Stub |

**Status:** ~30% complete (templates defined, execution missing)

### eden_engine/performance/optimizer.py
| Line | Issue | Priority | Type |
|------|-------|----------|------|
| All | Only type definitions (OptimizationType, OptimizationSuggestion) | LOW | Skeleton module |

**Status:** ~10% complete (no QueryAnalyzer, CallGraph, OptimizationAdvisor classes)

### eden_engine/performance/profiler.py
| Line | Issue | Priority | Type |
|------|-------|----------|------|
| All | Only type definitions (OperationType, TimingData) | LOW | Skeleton module |

**Status:** ~10% complete (no Profiler, OperationTimer, MetricsCollector classes)

### eden_engine/lexer/tokenizer.py
| Line | Issue | Priority | Type |
|------|-------|----------|------|
| 42-43 | `TokenizationError` - empty exception class | LOW | Exception stub |

**Status:** ✅ Functional (inherits from Exception)

### eden_engine/parser/parser.py
| Line | Issue | Priority | Type |
|------|-------|----------|------|
| 48-49 | `ParseError` - empty exception class | LOW | Exception stub |

**Status:** ✅ Functional (inherits from Exception)

### eden_engine/tests/unit/test_codegen_runtime.py
| Line | Issue | Priority | Type |
|------|-------|----------|------|
| 35 | Tests skipped - "Parser/Compiler modules not available" | **HIGH** | Skipped: ~150 tests |

**Impact:** Core compilation pipeline tests not running

### eden_engine/tests/unit/test_inheritance_caching.py
| Line | Issue | Priority | Type |
|------|-------|----------|------|
| 42 | Tests skipped - "Inheritance/Caching modules not available" | MEDIUM | Skipped: ~200 tests |

**Impact:** Template inheritance and cache tests not running

---

## eden/

### eden/auth/base.py
| Line | Issue | Priority | Type |
|------|-------|----------|------|
| 25-45 | `AuthBackend.authenticate()`, `.login()`, `.logout()` - abstract methods | LOW | Abstract methods |

**Status:** ✅ Implemented in subclasses (SessionBackend, JWTBackend, APIKeyBackend)

### eden/mail/backends.py
| Line | Issue | Priority | Type |
|------|-------|----------|------|
| 25-28 | `EmailBackend.send()` - abstract method | LOW | Abstract method |

**Status:** ✅ Implemented (ConsoleBackend, SMTPBackend)

### eden/storage.py
| Line | Issue | Priority | Type |
|------|-------|----------|------|
| 20-32 | `StorageBackend.save()`, `.delete()`, `.url()` - abstract methods | LOW | Abstract methods |

**Status:** ✅ Implemented (LocalStorageBackend, S3StorageBackend, SupabaseStorageBackend)

### eden/validators.py
| Line | Issue | Priority | Type |
|------|-------|----------|------|
| 766 | `_PydanticValidator._validate()` - raises NotImplementedError | LOW | Abstract/Override required |

**Status:** ✅ Implemented in subclasses (EdenEmail, EdenPassword, etc.)

### eden/responses.py
| Line | Issue | Priority | Type |
|------|-------|----------|------|
| 45-46 | `Response` - empty class (just inherits) | LOW | Pass stub |
| 82-83 | `HtmlResponse` - empty class (just inherits) | LOW | Pass stub |
| 86-87 | `RedirectResponse` - empty class (just inherits) | LOW | Pass stub |
| 98-99 | `FileResponse` - empty class (just inherits) | LOW | Pass stub |
| 103-104 | `StreamingResponse` - empty class (just inherits) | LOW | Pass stub |

**Status:** ✅ All functional via Starlette inheritance

### eden/storage_backends/s3.py
| Line | Issue | Priority | Type |
|------|-------|----------|------|
| None | Implementation appears complete | ✅ | Complete |

### eden/storage_backends/supabase.py
| Line | Issue | Priority | Type |
|------|-------|----------|------|
| None | Implementation appears complete | ✅ | Complete |

### eden/payments/providers.py
| Line | Issue | Priority | Type |
|------|-------|----------|------|
| Multiple | `PaymentProvider` - abstract methods with `...` | LOW | Abstract interface |

**Status:** ✅ Interface complete; implementations in Stripe backend

### eden/payments/models.py
| Line | Issue | Priority | Type |
|------|-------|----------|------|
| None | Models appear complete | ✅ | Complete |

### eden/payments/webhooks.py
| Line | Issue | Priority | Type |
|------|-------|----------|------|
| None | Implementation appears complete | ✅ | Complete |

### eden/realtime.py
| Line | Issue | Priority | Type |
|------|-------|----------|------|
| None | Implementation appears complete | ✅ | Complete |

### eden/satellite.py
| Line | Issue | Priority | Type |
|------|-------|----------|------|
| None | Implementation appears complete | ✅ | Complete |

### eden/openapi.py
| Line | Issue | Priority | Type |
|------|-------|----------|------|
| None | Implementation appears complete | ✅ | Complete |

### eden/telemetry.py
| Line | Issue | Priority | Type |
|------|-------|----------|------|
| None | Implementation appears complete | ✅ | Complete |

### eden/port.py
| Line | Issue | Priority | Type |
|------|-------|----------|------|
| None | Implementation appears complete | ✅ | Complete |

### eden/tasks/scheduler.py
| Line | Issue | Priority | Type |
|------|-------|----------|------|
| None | Implementation appears complete (CronExpression defined) | ✅ | Complete |

---

## eden/cli/

### eden/cli/main.py
| Line | Issue | Priority | Type |
|------|-------|----------|------|
| 25-27 | `cli()` - click group with just `pass` | LOW | Pass decorator |

**Status:** ✅ By design (subcommands implement functionality)

### eden/cli/forge.py
| Line | Issue | Priority | Type |
|------|-------|----------|------|
| 18-20 | `generate()` - click group with just `pass` | LOW | Pass decorator |

**Status:** ✅ By design (subcommands implement functionality)

### eden/cli/db.py
| Line | Issue | Priority | Type |
|------|-------|----------|------|
| 20-22 | `db()` - click group with just `pass` | LOW | Pass decorator |

**Status:** ✅ By design (subcommands implement functionality)

### eden/cli/auth.py
| Line | Issue | Priority | Type |
|------|-------|----------|------|
| 14-16 | `auth()` - click group with just `pass` | LOW | Pass decorator |

**Status:** ✅ By design (subcommands implement functionality)

### eden/cli/tasks.py
| Line | Issue | Priority | Type |
|------|-------|----------|------|
| 15-17 | `tasks()` - click group with just `pass` | LOW | Pass decorator |

**Status:** ✅ By design (subcommands implement functionality)

---

## examples/

### examples/07_production.py
| Line | Issue | Priority | Type |
|------|-------|----------|------|
| 113 | Metrics endpoint has TODO: `{"uptime": "TODO", "requests": "TODO"}` | LOW | TODO in example |

**Status:** Example file (not production code)

---

## Summary by File

### 🔴 CRITICAL Issues
- [ ] eden_engine/engine/core.py (render API)
- [ ] eden_engine/runtime/engine.py (safe execution)

### 🟠 HIGH Issues
- [ ] eden_engine/parser/ast_nodes.py (visitor pattern)
- [ ] eden_engine/compiler/codegen.py (visitor implementation)
- [ ] eden_engine/tests/unit/test_codegen_runtime.py (enable tests)

### 🟡 MEDIUM Issues
- [ ] eden_engine/performance/benchmarks.py (complete execution)
- [ ] eden_engine/inheritance/inheritance.py (verify implementations)
- [ ] eden_engine/tests/unit/test_inheritance_caching.py (enable tests)

### 🟢 LOW Issues (No Action Needed)
- ✅ eden/auth/base.py (implemented)
- ✅ eden/mail/backends.py (implemented)
- ✅ eden/storage.py (implemented)
- ✅ eden/responses.py (functional by inheritance)
- ✅ eden/cli/*.py (by design)
- ✅ Most other eden/auth, eden/storage, eden/payments modules

---

## Impact Summary

| Category | Count | Status |
|----------|-------|--------|
| CRITICAL Issues | 2 | Needs immediate fix |
| HIGH Issues | 5 | Needs urgent fix |
| MEDIUM Issues | 3 | Needs attention |
| LOW Issues | 20+ | No action needed |
| Complete Modules | 20+ | ✅ Ready |
| **Total Issues** | **30+** | |
| **Skipped Tests** | **~350+** | Tests blocked |

---

