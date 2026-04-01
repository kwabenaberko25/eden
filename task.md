# Production Hardening — Execution Tracker

## Phase 1: Security Hardening
- [ ] 1.1 — `app.py`: Replace hardcoded `secret_key` fallback with `RuntimeError` in prod
- [ ] 1.2 — `app.py`: Remove `"pytest" in sys.modules` heuristic from `is_test()`
- [ ] 1.3 — `app.py`: Delete duplicate `configure_mail()` (line 711-714)
- [ ] 1.4 — `app.py`: Delete duplicate `mount_admin()` (line 727-730)

## Phase 2: ContextManager Thread-Safety
- [ ] 2.1 — `context.py`: Add `_context_tokens` ContextVar for per-request token storage
- [ ] 2.2 — `context.py`: Rewrite `on_request_start()` to use ContextVar tokens
- [ ] 2.3 — `context.py`: Rewrite `on_request_end()` to use ContextVar tokens
- [ ] 2.4 — `context.py`: Update `set_user()`, `set_tenant()`, `set_organization()` 
- [ ] 2.5 — `context.py`: Update `clear()` method

## Phase 3: Observability & Silent Failures
- [ ] 3.1 — `config.py`: Change Redis URL default from `localhost:6379` to `""`
- [ ] 3.2 — Create `eden/diagnostics.py` startup diagnostics system
- [ ] 3.3 — `app.py`: Integrate diagnostics into Eden init/build
- [ ] 3.4 — Fix ALL `except Exception: pass` blocks across codebase (35 files)

## Phase 4: Lazy Imports & Config Isolation
- [ ] 4.1 — `eden/__init__.py`: Convert to `__getattr__`-based lazy imports (one-shot)
- [ ] 4.2 — `config.py`: Improve `reset()` documentation and test isolation guidance

## Verification
- [ ] 5.1 — Run full test suite
- [ ] 5.2 — Quick-import smoke test
- [ ] 5.3 — Verify no regressions
