# debug-eden-runtime Skill

**Fast, structured debugging for Eden Framework runtime errors.**

## Quick Start

When you hit an error:

1. **@mention the skill**: Share error message or test name
2. **Follow the workflow**: Reproduce → Isolate → Inspect → Fix → Verify
3. **Use supporting docs**: Check layer-specific diagnostics and common pitfalls

### Example Prompts

```
/debug-eden-runtime Test test_login fails with AttributeError: 'NoneType' has no attribute 'id'
```

```
/debug-eden-runtime Query returns data from wrong tenant. How do I isolate if it's a middleware or ORM issue?
```

```
/debug-eden-runtime Async task times out. Missing await? Wrong context?
```

---

## What's Included

- **SKILL.md** — The 5-step workflow with checklists and techniques
- **references/isolation-checklist.md** — Layer-specific diagnostics (ORM, middleware, templates, async, tenancy, auth)
- **references/common-pitfalls.md** — 12 known error patterns with examples
- **references/eden-layers.md** — Architecture overview for tracing errors
- **scripts/isolate-test.py** — Extract failing tests into standalone scripts

---

## The Workflow

### 1. **Reproduce** 
Get a repeatable error with minimal steps. `pytest -xvs` to isolate one failing test.

### 2. **Isolate**
Determine which layer (ORM, middleware, templates, async, tenancy, auth). Use isolation checklist.

### 3. **Inspect**
Understand the root cause (not just symptom). Read code, logs, and state.

### 4. **Fix**
Apply targeted fix. Minimal change, follows framework patterns.

### 5. **Verify**
Confirm fix works and doesn't break related code. Run tests.

---

## When to Use Each Reference

| Situation | Reference |
|-----------|-----------|
| "Which layer is this error in?" | [isolation-checklist.md](references/isolation-checklist.md) |
| "I keep seeing this error pattern" | [common-pitfalls.md](references/common-pitfalls.md) |
| "How does the framework architecture work?" | [eden-layers.md](references/eden-layers.md) |
| "I need to extract one failing test" | `scripts/isolate-test.py` |

---

## Example: Debugging a Test Failure

**Error**: `tests/auth/test_login.py::test_invalid_credentials` fails with `KeyError: 'tenant_id'`

**Step 1: Reproduce**
```bash
pytest tests/auth/test_login.py::test_invalid_credentials -xvs
```

**Step 2: Isolate**
- Error at line X in `middleware.py`
- Trying to access `request.headers['X-Tenant-ID']` but it's not there
- → Middleware issue, not ORM

**Step 3: Inspect**
- Check test setup: Does it provide tenant header?
- Check middleware: Is it expecting a header that tests don't provide?
- Root cause: Test fixture missing tenant context setup

**Step 4: Fix**
```python
# In test fixture
@pytest.fixture
def auth_client(client):
    client.headers["X-Tenant-ID"] = "test-tenant"  # ← ADD THIS
    return client
```

**Step 5: Verify**
```bash
pytest tests/auth/test_login.py::test_invalid_credentials -xvs  # ✅ PASS
pytest tests/auth/ -x                                            # ✅ All pass
```

---

## Common Error Patterns (Quick Reference)

| Error | Layer | First Check |
|-------|-------|-------------|
| `TypeError: 'coroutine' object is not...` | Async | Missing `await` |
| `KeyError: 'tenant_id'` | Middleware | Tenant header not in test |
| `AttributeError: 'NoneType' has no attribute` | ORM or Middleware | Query returned None or context not set |
| `IntegrityError: Foreign key` | Database | Parent record doesn't exist |
| `Template error: Unknown directive` | Templates | Directive not registered |
| `ContextVar value not found` | Async/Context | Running outside request context |

See [common-pitfalls.md](references/common-pitfalls.md) for full patterns with solutions.

---

## Tips

1. **Add logging first**: Before modifying code, add `logger.debug()` to trace execution
2. **Minimize reproduction**: Use `isolate-test.py` to extract failing test into standalone script
3. **Check the basics**: Missing await, wrong type, context not set? Check common pitfalls first
4. **Test in isolation**: Create minimal test fixtures to verify fix in isolation
5. **Check related code**: If you fix a pattern, search codebase for same issue

---

## Need Help?

- **Error crosses multiple layers?** Start with lowest layer (database), work upward
- **Not sure which layer?** Use the Choice Tree in [isolation-checklist.md](references/isolation-checklist.md)
- **Familiar error pattern?** Search [common-pitfalls.md](references/common-pitfalls.md)
- **Need architecture context?** Read [eden-layers.md](references/eden-layers.md)

---

## File Structure

```
debug-eden-runtime/
├── SKILL.md                           # Main 5-step workflow
├── README.md                          # This file
├── references/
│   ├── isolation-checklist.md        # Layer-specific diagnostics
│   ├── common-pitfalls.md            # 12 known error patterns
│   └── eden-layers.md                # Architecture overview
└── scripts/
    └── isolate-test.py               # Extract failing tests
```

---

## Success Criteria

You've successfully debugged when:

✅ Root cause identified (not just symptom fixed)  
✅ Minimal, targeted fix applied  
✅ Original failure now passes  
✅ Related tests still pass (no regressions)  
✅ Fix follows framework patterns  

---

## Next Steps After Debugging

1. **Write a test** covering the failure case
2. **Update docs** if pattern should be known
3. **Check similar code** for same issue elsewhere
4. **Review with team** if it's a significant architectural issue

---

Good luck! Use the skill, follow the checklist, and trace methodically. 🔍
