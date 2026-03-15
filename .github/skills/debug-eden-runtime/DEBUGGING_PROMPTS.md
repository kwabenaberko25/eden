# Debugging Prompts: Templates & Examples

Use these templates to get the most help when debugging Eden Framework issues.

---

## Template 1: Test Failure

```
/debug-eden-runtime #reproduce

**Test Name**: tests/path/to/test.py::TestClass::test_method

**Error Message**: [Copy full error/traceback here]

**Steps to Reproduce**:
```bash
pytest tests/path/to/test.py::TestClass::test_method -xvs
```

**Environment**:
- Python version: [e.g., 3.11.0]
- Database: [SQLite / PostgreSQL / MySQL]
- Key config: [Any relevant settings]

**What I've tried**:
- [Something you already tested]
```

### Example Output
```
I'm stuck on test_user_login_with_invalid_credentials failing with:
KeyError: 'tenant_id' at eden/middleware.py:45

Steps to reproduce:
```bash
pytest tests/auth/test_login.py::test_user_login_with_invalid_credentials -xvs
```

Environment:
- Python 3.11
- SQLite (in-memory for tests)
- No special config

What I've tried:
- Ran test in isolation; same error
- Checked that auth middleware is registered
```

---

## Template 2: Isolate the Layer

```
/debug-eden-runtime #isolate

**Error**: [Brief description]

**Symptoms**: [What happens]

**Where I think it is**: 
- ORM (queries/models)?
- Middleware (auth/context)?
- Templates?
- Async tasks?
- Multi-tenancy?
- Other?

**Evidence**:
- Log snippet: [Relevant logs]
- Stack trace: [Last few lines showing origin]
- Code context: [Code around error]
```

### Example
```
Error: Query returns data from wrong tenant

Symptoms: User from tenant_a sees data from tenant_b

Where I think it is:
- Could be ORM not filtering by tenant
- Could be middleware not setting tenant context

Evidence:
- Stack trace shows: user_service.py:45 → query_builder.py:130 → orm.py:892
- Log shows: "Querying users with filter: {}" (no tenant_id!)
```

---

## Template 3: Inspect & Root Cause

```
/debug-eden-runtime #inspect

**Component**: [What's failing]

**Root Cause Hypothesis**: [What do you think is wrong]

**Evidence**:
- Variable state: [Values printed/logged]
- Database state: [What's in the DB]
- Code review: [What looks wrong]

**Related Code**:
[Paste 5-10 lines of code]
```

### Example
```
Component: TenantMiddleware not setting tenant context

Root Cause Hypothesis: Middleware expects X-Tenant-ID header but test doesn't send it

Evidence:
- Logged request.headers: {'Authorization': 'Bearer ...', 'Accept': 'application/json'}
  (No X-Tenant-ID!)
- Code in middleware: tenant_id = request.headers.get("X-Tenant-ID")
  (Returns None if not present)

Related Code:
```python
@app.middleware
async def tenant_middleware(request, call_next):
    tenant_id = request.headers.get("X-Tenant-ID")
    set_current_tenant(tenant_id)  # <-- Sets None!
    return await call_next(request)
```
```

---

## Template 4: Verify the Fix

```
/debug-eden-runtime #verify

**Fix Applied**: [Describe what changed]

**Test Results**:
- Original test: [PASS / FAIL]
- Related tests: [number that pass/fail]
- Full suite: [any failures?]

**Checks**:
- [ ] No hardcoded values
- [ ] Error handling present
- [ ] Logging added
- [ ] Follows framework patterns
```

### Example
```
Fix Applied:
Added tenant header to test fixture:
```python
@pytest.fixture
def auth_client(client):
    client.headers["X-Tenant-ID"] = "test-tenant"
    return client
```

Test Results:
- Original test (test_invalid_credentials): PASS ✅
- Related tests (tests/auth/): 8 pass ✅
- Full suite: 127 pass ✅

Checks:
- [x] No hardcoded values (using fixture constant)
- [x] Error handling present (N/A for this fix)
- [x] Logging added (N/A)
- [x] Follows framework patterns (fixture pattern)
```

---

## Anti-Patterns: What NOT to Do

### ❌ Too Vague
```
i have an error pls help
```
*Better*:
```
Test test_login fails with AttributeError at line 45 of auth.py
```

### ❌ Too Much Code
```
Here's my entire test file with 500 lines...
```
*Better*:
```
Here's the failing test and the setup fixture it uses (30 lines)
```

### ❌ No Context
```
Getting KeyError: 'user_id'
```
*Better*:
```
Getting KeyError: 'user_id' in UserService.get_user() when tenant context not set
```

---

## Quick Access by Situation

### "Test fails, not sure where to start"
Use **Template 1** → Provide full error so we can help isolate

### "I know what layer it's in, need to confirm"
Use **Template 2** → Help narrow down to exact component

### "I found the issue, does this look like the cause?"
Use **Template 3** → Review your analysis and confirm

### "I fixed it, is this solid?"
Use **Template 4** → Verify fix is complete and doesn't break anything

---

## Checklists for Each Phase

### Reproduce Phase Checklist
- [ ] Error is repeatable (happens > once)
- [ ] Reproduces in isolation (not dependent on other tests)
- [ ] Full error/traceback captured
- [ ] Environment documented

### Isolate Phase Checklist
- [ ] Layer identified (ORM/middleware/templates/async/tenancy/auth)
- [ ] Call stack traced
- [ ] Related code reviewed

### Inspect Phase Checklist
- [ ] Root cause hypothesis formed
- [ ] Evidence gathered (logs, state, code)
- [ ] Assumptions listed

### Fix Phase Checklist
- [ ] Fix addresses root cause (not symptom)
- [ ] Minimal change (no scope creep)
- [ ] Error handling explicit
- [ ] Logging present

### Verify Phase Checklist
- [ ] Original test passes
- [ ] Related tests pass
- [ ] Full suite passes
- [ ] No regressions

---

## Success Example: Full Workflow

**User Message**:
```
/debug-eden-runtime

Test: tests/auth/test_login.py::test_user_login_with_invalid_tenant
Error: KeyError: 'tenant_id' at eden/middleware.py:45

Environment: Python 3.11, SQLite

I've added logging and found:
- Middleware expects X-Tenant-ID header
- Test doesn't send it
- So tenant_id becomes None

Is this the issue?
```

**Result**: Skill confirms root cause, suggests fix, we verify.

---

## Getting Maximum Value

1. **Copy the right template** for your situation
2. **Fill in all sections** (don't skip context)
3. **Include evidence** (logs, code, state)
4. **Ask specific questions** (not just "why does it fail?")
5. **Include next steps** ("if it's X, I'll do Y")

This helps the skill give you **targeted, actionable** debugging help instead of generic troubleshooting steps.

---

## Related

- [SKILL.md](../SKILL.md) — Full workflow
- [isolation-checklist.md](../references/isolation-checklist.md) — Layer diagnostics
- [common-pitfalls.md](../references/common-pitfalls.md) — Error patterns
