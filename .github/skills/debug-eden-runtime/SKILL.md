---
name: debug-eden-runtime
description: 'Debug runtime errors in the Eden Framework. Use when: test failures, exceptions, crashes, unexpected behavior. Provides linear workflow: Reproduce → Isolate → Inspect → Fix → Verify with root cause focus.'
argument-hint: 'Error message, test name, or behavior to diagnose'
---

# Debug Eden Framework Runtime Errors

## When to Use

- **Test failures** or pytest crashes
- **Exceptions** during development or production
- **Unexpected behavior** (wrong output, silent failures, state corruption)
- **Integration issues** between layers (ORM, middleware, components, templates)
- **Async/concurrency bugs** (context vars, task execution)
- **Multi-tenant isolation breaches**

## Overview

This skill provides a **5-step linear debugging workflow** designed for the Eden Framework's multi-layered architecture. Each step includes a checklist and diagnostic questions to identify root causes, not just symptoms.

**Workflow:**
```
Reproduce → Isolate → Inspect → Fix → Verify
```

---

## Step 1: Reproduce

### Goal
Reliably trigger the error in a controlled environment.

### Checklist
- [ ] Error repeats consistently (not intermittent)
- [ ] Error occurs in isolation (not dependent on other tests)
- [ ] Minimal reproduction case identified (fewest steps to trigger)
- [ ] Environment confirmed (Python version, dependencies, .env)
- [ ] Related tests all passing before change?

### Key Questions
- When did this start? (After which code change?)
- Does it happen locally? On CI? Everywhere?
- Is data/state required? (Setup fixtures, database state)
- Are there timing-dependent aspects? (Async, race conditions, timeouts)
- Does it depend on external services? (Database, cache, email)

### Tools
- Use [./scripts/isolate-test.py](./scripts/isolate-test.py) to extract failing test into standalone script
- Review [../references/eden-layers.md](../references/eden-layers.md) if error crosses multiple subsystems

---

## Step 2: Isolate

### Goal
Identify which subsystem/layer the error originates from.

### Checklist
- [ ] Error occurs in ORM layer (models, queries, migrations)?
- [ ] Error occurs in middleware/request handling?
- [ ] Error occurs in templates/rendering?
- [ ] Error occurs in async/task execution?
- [ ] Error occurs in multi-tenancy/context vars?
- [ ] Error is a cascading failure from upstream layer?

### Diagnostic Questions
- Does disabling middleware stop the error?
- Does using raw SQL bypass the error?
- Does mocking dependencies eliminate the error?
- What's the call stack? (Which function called which?)
- Is the error deterministic based on user input, or system state?

### Subsystem Focus Areas
Use [../references/isolation-checklist.md](../references/isolation-checklist.md) for layer-specific diagnostics:
- **ORM Issues**: Query structure, transaction handling, schema/tenant mismatches
- **Middleware**: CSRF, auth, session binding, header parsing
- **Templates**: Directive parsing, context binding, escape/injection
- **Async**: Context var handling, task execution, event loop blocking
- **Multi-Tenant**: Tenant context, schema validation, query isolation

---

## Step 3: Inspect

### Goal
Examine code, logs, and state to understand what actually happened.

### Checklist
- [ ] Full stack trace captured (with local variable inspection)
- [ ] Relevant logs reviewed and filtered by timestamp
- [ ] Code path traced through calling functions
- [ ] Assumptions explicitly listed (what should happen vs. what did)
- [ ] Related test/fixture code reviewed

### Inspection Techniques
1. **Add strategic logging** — Don't just look at existing logs; add print/logger calls to trace execution flow
2. **Review assertion failures** — pytest output shows expected vs. actual; check data types, nulls, formatting
3. **Inspect intermediate state** — If error is on line N, what were values on lines N-5 through N-1?
4. **Check configuration** — Missing env vars, wrong settings, mismatched versions
5. **Examine fixtures** — Are test fixtures setting up correct state?

### Common Eden Pitfalls
Use [../references/common-pitfalls.md](../references/common-pitfalls.md) for known failure patterns:
- Context vars not set/reset properly
- Tenant schema isolation bypassed
- Async/await confusion (missing await, event loop interference)
- Template directive edge cases
- Dependency injection misconfig

---

## Step 4: Fix

### Goal
Implement a solution that addresses the root cause (not the symptom).

### Checklist
- [ ] Root cause clearly understood and documented
- [ ] Fix targets root cause (not workaround)
- [ ] Fix doesn't break related functionality
- [ ] Error handling is explicit (not silent)
- [ ] Logging added for future diagnostics

### Approach
1. **Confirm root cause hypothesis** — Can you predict and prevent the error by changing one thing?
2. **Choose the fix** — Is it a code change, config fix, migration, or test setup?
3. **Consider regression** — Does this fix introduce new risks? Check [../references/common-pitfalls.md](../references/common-pitfalls.md) for related issues
4. **Implement concisely** — Minimal change; avoid scope creep
5. **Add guards** — Assertions, type hints, or early returns to prevent similar errors

### Implementation Checklist
- [ ] Code is syntactically valid (imports, indentation)
- [ ] Type hints are present (if Python)
- [ ] Error messages are descriptive (not "Something went wrong")
- [ ] Logs added for debugging future issues
- [ ] Related code reviewed for similar bugs

---

## Step 5: Verify

### Goal
Confirm the fix works and doesn't cause regressions.

### Checklist
- [ ] Original failing test/case now passes
- [ ] Related tests still pass (no regression)
- [ ] Functionality tested manually (if applicable)
- [ ] Edge cases considered and tested
- [ ] Code review completed (if team-based)

### Verification Pproach
```bash
# 1. Run the specific failing test
pytest tests/path/to/test.py::test_name -xvs

# 2. Run related tests (same subsystem)
pytest tests/path/to/ -k "keyword" -x

# 3. Full test suite (catch regressions)
pytest tests/ --tb=short

# 4. Check type hints (if applicable)
mypy eden/ --ignore-missing-imports
```

### Exit Criteria
- ✅ Failing test passes consistently
- ✅ No new test failures introduced
- ✅ Code follows project conventions
- ✅ Root cause documented in commit message or issue

---

## Example Workflow

**Scenario**: Test `test_user_login_with_invalid_tenant` fails with `KeyError: 'tenant_id'`

### Step 1: Reproduce
```bash
pytest tests/auth/test_login.py::test_user_login_with_invalid_tenant -xvs
# Error: KeyError: 'tenant_id' at eden/middleware.py:45
```

### Step 2: Isolate
- Is this a middleware issue? Add logging around tenant_id extraction
- Is this a test setup issue? Review fixture for tenant context
- Is this multi-tenancy-specific? Check TenantMiddleware

### Step 3: Inspect
- View stack trace: middleware → request handler → ORM query
- Log tenant_id value before it's used
- Check fixture: Is tenant context being set correctly?

### Step 4: Fix
- Found: TenantMiddleware expects `request.headers['X-Tenant-ID']`, but test doesn't set it
- Root cause: Test fixture missing tenant header setup
- Fix: Add `headers={'X-Tenant-ID': 'test-tenant'}` to test client

### Step 5: Verify
```bash
pytest tests/auth/test_login.py::test_user_login_with_invalid_tenant -xvs  # PASS
pytest tests/auth/ -x  # All pass
pytest tests/ -x  # Full suite pass
```

---

## Resources

- [Isolation Checklist](../references/isolation-checklist.md) — Layer-specific diagnostics
- [Common Pitfalls](../references/common-pitfalls.md) — Known Eden Framework error patterns
- [Eden Layers Overview](../references/eden-layers.md) — Architecture reference for tracing errors
- [Scripts](./scripts/) — Tools for debugging (log parsing, test isolation, etc.)

---

## Quick Tips

| Issue | Quick Check |
|-------|-------------|
| "Module not found" | Check imports, PYTHONPATH, virtual environment activated |
| "Unexpected None" | Add assertion in test or try/except with descriptive error |
| "Context var not set" | Check request middleware setup, timing of set_current_tenant() |
| "Query returns wrong data" | Verify tenant/schema isolation, check SQL log output |
| "Async timeout" | Check for blocking I/O in async context, missing await |
| "Test setup fails" | Run test in isolation, check fixtures, verify DB migration |

