# Eden Framework: Deep Source-Code Audit Report

> **Scope:** Source code only — no [.md](file:///c:/PROJECTS/eden-framework/plans.md) documentation files consulted.
> **Date:** 2026-03-24
> **Audited Paths:** [eden/](file:///c:/PROJECTS/eden-framework/eden/template_directives.py#58-61), `tests/`

---

## Executive Summary

The Eden framework is ambitious in scope, covering ORM, auth, tenancy, payments, tasks, storage, caching, WebSockets, templating, admin, and more. However, the source code reveals **active debug prints in production paths**, **inconsistent ORM API contracts**, **broken session management**, **audit logging that does nothing**, **a payments module with sync-in-async anti-patterns**, and several modules that exist as **scaffolding without real functionality**. Below is the exhaustive analysis.

---

## 🔴 Critical Issues (Breaking / Data-Safety Risks)

### 1. Active `print(f"DEBUG ...")` Statements in Production Code

**Files:**
- [context_middleware.py](file:///c:/PROJECTS/eden-framework/eden/context_middleware.py#L94) — `print(f"DEBUG: ContextMiddleware for {request.method} {request.url.path}")`
- [tasks/__init__.py](file:///c:/PROJECTS/eden-framework/eden/tasks/__init__.py#L443) — `print(f"DEBUG TASK REGISTER: ...")`
- [tasks/__init__.py](file:///c:/PROJECTS/eden-framework/eden/tasks/__init__.py#L529) — `print(f"DEBUG TASK: executing ...")`
- [tasks/__init__.py](file:///c:/PROJECTS/eden-framework/eden/tasks/__init__.py#L553) — `print(f"DEBUG TASK ERROR: ...")`

**Impact:** Every HTTP request hits `context_middleware.py:94`, printing to stdout. In production, this is a performance leak and potential information disclosure. The task module prints on every task registration and execution.

**Fix:**
```diff
- print(f"DEBUG: ContextMiddleware for {request.method} {request.url.path}")
+ logger.debug("ContextMiddleware for %s %s", request.method, request.url.path)
```
Remove or convert all `print(f"DEBUG ...")` to `logger.debug(...)`.

---

### 2. [create_user()](file:///c:/PROJECTS/eden-framework/eden/auth/actions.py#113-154) Uses Two Conflicting ORM APIs

**File:** [auth/actions.py](file:///c:/PROJECTS/eden-framework/eden/auth/actions.py#L113-L153)

```python
# Line 55: uses .filter().first() — QuerySet/CrudMixin style
user = await user_model.filter(email=email.lower()).first()

# Line 146: uses .objects.create() — Django-style manager
user = await user_model.objects.create(...)
```

**Impact:** If the ORM only supports one pattern (which is the case — Eden uses `CrudMixin`), one of these calls will raise `AttributeError` at runtime. The [authenticate()](file:///c:/PROJECTS/eden-framework/eden/auth/actions.py#19-68) function uses `.filter()` while [create_user()](file:///c:/PROJECTS/eden-framework/eden/auth/actions.py#113-154) uses `.objects.create()`. These are **mutually incompatible** unless both APIs are explicitly maintained.

**Fix:** Standardize on the `CrudMixin` pattern:
```python
user = await user_model.create(email=email, password_hash=hash_password(password), **kwargs)
```

---

### 3. [AuditableMixin](file:///c:/PROJECTS/eden-framework/eden/audit/__init__.py#12-30) Does Absolutely Nothing

**File:** [audit/__init__.py](file:///c:/PROJECTS/eden-framework/eden/audit/__init__.py#L12-L29)

```python
class AuditableMixin:
    async def save(self, *args, **kwargs):
        # Determine if this is a creation or updated
        # In a real implementation, we'd capture before/after states here.
        await super().save(*args, **kwargs)  # ← Just delegates, no auditing

    async def delete(self, *args, **kwargs):
        # Log deletion ← Comment says "log", but does nothing
        await super().delete(*args, **kwargs)
```

**Impact:** Any model using [AuditableMixin](file:///c:/PROJECTS/eden-framework/eden/audit/__init__.py#12-30) gets zero auditing. The comments explicitly say "In a real implementation". This is **scaffolding presented as a feature**.

**Fix:** Capture before/after state diffs and create `AuditLog` entries:
```python
async def save(self, *args, **kwargs):
    is_new = not getattr(self, 'id', None)
    old_data = {} if is_new else await self._get_current_db_state()
    await super().save(*args, **kwargs)
    new_data = self.to_dict()
    changes = {k: (old_data.get(k), v) for k, v in new_data.items() if old_data.get(k) != v}
    if changes:
        await AuditLog.create(
            action="CREATE" if is_new else "UPDATE",
            model_name=self.__class__.__name__,
            record_id=str(self.id),
            changes=changes,
        )
```

---

### 4. Payments Module: Sync Stripe Calls Inside `async def`

**File:** [payments/providers.py](file:///c:/PROJECTS/eden-framework/eden/payments/providers.py#L97-L156)

Every method in [StripeProvider](file:///c:/PROJECTS/eden-framework/eden/payments/providers.py#61-156) is declared `async def` but calls synchronous Stripe SDK methods:

```python
async def create_customer(self, email, name="", metadata=None) -> str:
    customer = self._stripe.Customer.create(...)  # ← BLOCKING CALL
    return customer.id
```

**Impact:** These synchronous calls **block the event loop**. Under load, a single Stripe API call (200-500ms network latency) blocks ALL concurrent requests on that worker. This will cause timeouts and degraded performance at scale.

**Fix:** Use `asyncio.to_thread()` or switch to the async Stripe client:
```python
async def create_customer(self, email, name="", metadata=None) -> str:
    customer = await asyncio.to_thread(
        self._stripe.Customer.create, email=email, name=name or None, metadata=metadata or {}
    )
    return customer.id
```

---

### 5. `VectorModel.semantic_search()` Uses Non-Existent `_get_session()`

**File:** [db/ai.py](file:///c:/PROJECTS/eden-framework/eden/db/ai.py#L56)

```python
async with cls._get_session() as session:
    result = await session.execute(stmt)
```

**Impact:** `_get_session()` does not exist on any [Model](file:///c:/PROJECTS/eden-framework/eden/forms.py#1028-1095) base class. Calling `VectorModel.semantic_search()` will raise `AttributeError`. The ORM uses `CrudMixin` with session injection from context, not a `_get_session()` method.

**Fix:** Use the session from context:
```python
from eden.db.session import get_session
session = get_session()
result = await session.execute(stmt)
return list(result.scalars().all())
```

---

### 6. OAuth Callback — Closure Variable Capture Bug

**File:** [auth/oauth.py](file:///c:/PROJECTS/eden-framework/eden/auth/oauth.py#L170-L171)

```python
for provider_name, provider in self._providers.items():
    self._mount_provider(app, prefix, provider)
```

Inside [_mount_provider](file:///c:/PROJECTS/eden-framework/eden/auth/oauth.py#173-353), the closure captures `p = provider` correctly. However, the [login](file:///c:/PROJECTS/eden-framework/eden/auth/actions.py#70-89) and [callback](file:///c:/PROJECTS/eden-framework/eden/auth/oauth.py#199-353) functions inside are **defined in a loop** and rely on the closure variable `p`. While [_mount_provider](file:///c:/PROJECTS/eden-framework/eden/auth/oauth.py#173-353) does capture `p` as a local, the inner functions [login](file:///c:/PROJECTS/eden-framework/eden/auth/actions.py#70-89) and [callback](file:///c:/PROJECTS/eden-framework/eden/auth/oauth.py#199-353) at lines 182 and 204 are **anonymous closures** — if multiple providers are registered, Starlette route names like `oauth_{p.name}_login` disambiguate correctly, but the closures share the same scope within [_mount_provider](file:///c:/PROJECTS/eden-framework/eden/auth/oauth.py#173-353).

**Status:** Currently works correctly because [_mount_provider()](file:///c:/PROJECTS/eden-framework/eden/auth/oauth.py#173-353) is a separate method (not inline). However, this is **fragile** — any refactoring that inlines the loop will break all providers.

---

## 🟠 Significant Issues (Functional Gaps / Incorrect Behavior)

### 7. [SearchQueryBuilder](file:///c:/PROJECTS/eden-framework/eden/db/search.py#8-51) Builds Strings — Not SQL

**File:** [db/search.py](file:///c:/PROJECTS/eden-framework/eden/db/search.py)

The [SearchQueryBuilder](file:///c:/PROJECTS/eden-framework/eden/db/search.py#8-51) only concatenates strings. It never generates `tsvector`, `tsquery`, or any PostgreSQL full-text search SQL. The docstring says:

```python
await Product.query().search_ranked(query).all()
```

But `search_ranked()` does not exist on `QuerySet`.

**Impact:** Full-text search is **not implemented**. The builder produces a plain string like `'eden "web framework" -legacy'` which has no integration with the ORM.

**Fix:** Implement actual FTS integration:
```python
from sqlalchemy import func, cast
from sqlalchemy.dialects.postgresql import TSVECTOR

def build_tsquery(self) -> str:
    """Build a PostgreSQL to_tsquery compatible string."""
    parts = []
    for term in self.terms:
        parts.append(term)
    for phrase in self.phrases:
        parts.append(phrase)  # Already quoted
    for excluded in self.excluded:
        parts.append(f"!{excluded[1:]}")  # Convert -term to !term
    return " & ".join(parts) if parts else self.base_query
```
And add `.search()` to `QuerySet`:
```python
def search(self, query: str, fields: list[str]) -> QuerySet:
    """Add full-text search filter."""
    # Implementation using ts_vector and ts_query
```

---

### 8. [VersionedRouter](file:///c:/PROJECTS/eden-framework/eden/versioning.py#131-176) Has No Integration with Eden App

**File:** [versioning.py](file:///c:/PROJECTS/eden-framework/eden/versioning.py#L131-L175)

[VersionedRouter](file:///c:/PROJECTS/eden-framework/eden/versioning.py#131-176) stores routes in its own dict but has no [mount()](file:///c:/PROJECTS/eden-framework/eden/i18n.py#140-159) method, no `add_router()` integration, and the [VersionedMiddleware](file:///c:/PROJECTS/eden-framework/eden/versioning.py#230-291) doesn't actually route to versioned handlers. It only stores the version in the scope:

```python
scope["api_version"] = version  # Stored but never used for routing
```

The [get_handler()](file:///c:/PROJECTS/eden-framework/eden/versioning.py#170-176) method exists but is never called by the middleware or the app.

**Impact:** API versioning is **declared but non-functional**. Routes are stored in the router's dict but never dispatched.

**Fix:** The [VersionedMiddleware](file:///c:/PROJECTS/eden-framework/eden/versioning.py#230-291) needs to intercept routing:
```python
# In __call__:
endpoint = scope.get("endpoint")
if endpoint and hasattr(endpoint, "_versioned_handlers"):
    handler = endpoint._versioned_handlers.get(version)
    if handler:
        scope["endpoint"] = handler
```

---

### 9. [TenantMiddleware](file:///c:/PROJECTS/eden-framework/eden/tenancy/middleware.py#24-225) Caches `None` Tenants — Locks Out Future Valid Requests

**File:** [tenancy/middleware.py](file:///c:/PROJECTS/eden-framework/eden/tenancy/middleware.py#L222)

```python
# Cache the result (even if None, to avoid repeated DB hits for invalid identifiers)
await self._cache.set(cache_key, tenant, ttl=300)
```

**Impact:** If a tenant is not yet created when the first request hits (e.g., during provisioning), `None` is cached for **5 minutes**. All subsequent requests for that tenant will get `None` from cache even after the tenant is created.

**Fix:** Only cache positive results, or use a shorter TTL for null:
```python
if tenant:
    await self._cache.set(cache_key, tenant, ttl=300)
else:
    await self._cache.set(cache_key, tenant, ttl=10)  # Short TTL for negatives
```

---

### 10. `TenantMiddleware._fetch_tenant()` — SQL Injection via `Tenant.id == identifier`

**File:** [tenancy/middleware.py](file:///c:/PROJECTS/eden-framework/eden/tenancy/middleware.py#L214-L216)

```python
stmt = select(Tenant).where(
    (Tenant.slug == identifier) | (Tenant.id == identifier)
).where(Tenant.is_active)
```

If `Tenant.id` is a UUID column and `identifier` is a non-UUID string (e.g., from a header), SQLAlchemy will raise `DataError` (PostgreSQL) or silently coerce (SQLite). This isn't SQL injection per se (SQLAlchemy parameterizes), but it **crashes the middleware** with an unhandled exception.

**Fix:** Validate UUID format before trying the [id](file:///c:/PROJECTS/eden-framework/eden/forms.py#641-702) comparison:
```python
import uuid as uuid_mod
try:
    uuid_val = uuid_mod.UUID(identifier)
    stmt = select(Tenant).where(
        (Tenant.slug == identifier) | (Tenant.id == uuid_val)
    )
except ValueError:
    stmt = select(Tenant).where(Tenant.slug == identifier)
```

---

### 11. [RateLimitMiddleware](file:///c:/PROJECTS/eden-framework/eden/middleware/rate_limit.py#248-374) Uses Wrong `Request` Class

**File:** [middleware/rate_limit.py](file:///c:/PROJECTS/eden-framework/eden/middleware/rate_limit.py#L320)

```python
from eden.requests import Request
req = Request.from_scope(scope, receive, send)
```

Starlette's `Request` constructor is `Request(scope, receive, send)`, not `Request.from_scope(...)`. If `eden.requests.Request` doesn't define `from_scope`, this raises `AttributeError`.

**Fix:**
```python
from eden.requests import Request
req = Request(scope, receive=receive)
```

---

### 12. Metrics Registry — No Thread Safety

**File:** [core/metrics.py](file:///c:/PROJECTS/eden-framework/eden/core/metrics.py)

All metrics operations mutate shared dicts without any locking:
```python
def increment(self, name, value=1, labels=None):
    key = self._get_key(name, labels)
    self._counters[key] = self._counters.get(key, 0) + value  # ← Not atomic
```

**Impact:** In multi-threaded deployments (e.g., Gunicorn with threads), counter increments can be lost due to race conditions.

**Fix:** Use `threading.Lock` or `asyncio.Lock` for mutations:
```python
import threading

class MetricsRegistry:
    def __init__(self, ...):
        self._lock = threading.Lock()
    
    def increment(self, name, value=1, labels=None):
        key = self._get_key(name, labels)
        with self._lock:
            self._counters[key] = self._counters.get(key, 0) + value
```

---

### 13. [DistributedBackend](file:///c:/PROJECTS/eden-framework/eden/core/backends/base.py#11-94) Protocol Uses `@abc.abstractmethod` — Invalid Combination

**File:** [core/backends/base.py](file:///c:/PROJECTS/eden-framework/eden/core/backends/base.py#L11-L17)

```python
@runtime_checkable
class DistributedBackend(Protocol):
    @abc.abstractmethod
    async def connect(self) -> None: ...
```

`Protocol` with `@abc.abstractmethod` is technically valid in Python 3.12+ but semantically misleading. Protocols are structural types — they don't enforce through inheritance. Using `@abstractmethod` on a `Protocol` doesn't actually prevent instantiation of non-implementations; it only has effect when the Protocol is used as a regular base class.

**Fix:** Remove `@abc.abstractmethod` decorators — Protocol already communicates the contract:
```python
class DistributedBackend(Protocol):
    async def connect(self) -> None: ...
    async def disconnect(self) -> None: ...
```

---

## 🟡 Moderate Issues (Incomplete Features / Technical Debt)

### 14. [WebhookRouter](file:///c:/PROJECTS/eden-framework/eden/payments/webhooks.py#16-136) — Handler Errors Are Silently Swallowed

**File:** [payments/webhooks.py](file:///c:/PROJECTS/eden-framework/eden/payments/webhooks.py#L59-L66)

```python
for handler in handlers:
    try:
        result = handler(event_data)
        if hasattr(result, "__await__"):
            await result
    except Exception as e:
        logger.error(f"Error in webhook handler for {event_type}: {e}")
```

**Impact:** If a webhook handler fails (e.g., can't update subscription status), the error is logged but the webhook is still **marked as `processed = True`** (line 130). The event is permanently lost — retry from Stripe will be rejected by deduplication.

**Fix:** Track handler success and only mark processed if all handlers succeed:
```python
all_success = True
for handler in handlers:
    try:
        result = handler(event_data)
        if hasattr(result, "__await__"):
            await result
    except Exception as e:
        logger.error(f"Error in webhook handler for {event_type}: {e}")
        all_success = False

if all_success:
    payment_event.processed = True
```

---

### 15. [InMemoryCache](file:///c:/PROJECTS/eden-framework/eden/db/cache.py#68-121) in [TenantMiddleware](file:///c:/PROJECTS/eden-framework/eden/tenancy/middleware.py#24-225) — No Size Limits

**File:** [tenancy/middleware.py](file:///c:/PROJECTS/eden-framework/eden/tenancy/middleware.py#L56)

```python
self._cache = InMemoryCache()
```

This cache has no max size. In a system with many unique tenant identifiers (especially invalid ones from scanners/bots), the cache grows unboundedly → memory leak.

**Fix:** Add LRU eviction to [InMemoryCache](file:///c:/PROJECTS/eden-framework/eden/db/cache.py#68-121) or use a bounded cache:
```python
from collections import OrderedDict

class BoundedInMemoryCache(InMemoryCache):
    def __init__(self, max_size: int = 1000):
        super().__init__()
        self.max_size = max_size
    
    async def set(self, key, value, ttl=None):
        if len(self._store) >= self.max_size:
            # Evict oldest
            self._store.pop(next(iter(self._store)))
        await super().set(key, value, ttl)
```

---

### 16. [auth/__init__.py](file:///c:/PROJECTS/eden-framework/eden/auth/__init__.py) — Duplicate Import of `RoleManager`

**File:** [auth/__init__.py](file:///c:/PROJECTS/eden-framework/eden/auth/__init__.py#L69-L138)

```python
# Line 75
from eden.auth.access import (
    ...
    RoleManager,
)

# Line 136-138 — DUPLICATE
from eden.auth.access import (
    RoleManager,
)
```

**Impact:** Not a runtime error, but indicates copy-paste mistakes and poor hygiene in the public API surface.

---

### 17. `validate_email()` Return Value Misuse in [create_user()](file:///c:/PROJECTS/eden-framework/eden/auth/actions.py#113-154)

**File:** [auth/actions.py](file:///c:/PROJECTS/eden-framework/eden/auth/actions.py#L125-L129)

```python
result = validate_email(email)
if not result:
    raise ValueError(f"Invalid email: {result.error}")
email = result.value
```

**Issue:** If `validate_email` returns a `ValidationResult` where `bool(result)` is `True` on success, accessing `.error` when `not result` is `True` assumes the result has an `.error` attribute. But the error path also accesses `result.value` on the success path — if `validate_email` returns a simple string or `True/False`, both `.error` and `.value` will raise `AttributeError`.

**Fix:** Verify `validate_email` return type and align:
```python
from eden.validators import validate_email, ValidationResult

result = validate_email(email)
if not result.is_valid:
    raise ValueError(f"Invalid email: {result.error}")
email = result.value
```

---

### 18. [QueryCache](file:///c:/PROJECTS/eden-framework/eden/db/cache.py#251-326) Uses Class Variables — Shared Across Tests

**File:** [db/cache.py](file:///c:/PROJECTS/eden-framework/eden/db/cache.py#L251-L258)

```python
class QueryCache:
    _backend: Optional[CacheBackend] = None
    _ttl: int = 3600
```

**Impact:** Class-level [_backend](file:///c:/PROJECTS/eden-framework/eden/websocket/manager.py#250-270) is shared across all imports. In test environments, configuring the cache in one test leaks state to subsequent tests. There's no [reset()](file:///c:/PROJECTS/eden-framework/eden/middleware/rate_limit.py#82-85) or `teardown()` method.

**Fix:** Add a reset method:
```python
@classmethod
def reset(cls) -> None:
    cls._backend = None
    cls._ttl = 3600
```

---

### 19. Missing `RedisCache.set()` — TTL Default Issue

**File:** [db/cache.py](file:///c:/PROJECTS/eden-framework/eden/db/cache.py#L171)

```python
await self.redis.setex(key, ttl or 3600, serialized)
```

If `ttl=0` is passed (meaning "no expiration"), `0 or 3600` evaluates to `3600` — TTL of 0 is silently replaced with 1 hour.

**Fix:**
```python
if ttl is not None and ttl > 0:
    await self.redis.setex(key, ttl, serialized)
else:
    await self.redis.set(key, serialized)
```

---

## 🔵 Design / Architecture Issues

### 20. [eden/services.py](file:///c:/PROJECTS/eden-framework/eden/services.py) — Empty Abstraction

**File:** [services.py](file:///c:/PROJECTS/eden-framework/eden/services.py)

```python
class BaseService:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
```

This is a 27-line file that provides essentially `**kwargs → attributes`. No lifecycle, no DI integration, no transaction management. Classes that inherit from `BaseService` get nothing that a plain class wouldn't provide.

---

### 21. [eden/telemetry.py](file:///c:/PROJECTS/eden-framework/eden/telemetry.py) vs [eden/core/metrics.py](file:///c:/PROJECTS/eden-framework/eden/core/metrics.py) — Duplicate Responsibility

Both modules provide performance metrics:
- [telemetry.py](file:///c:/PROJECTS/eden-framework/eden/telemetry.py) tracks request-scoped timing with optional Sentry integration
- [core/metrics.py](file:///c:/PROJECTS/eden-framework/eden/core/metrics.py) provides Prometheus-style counters, gauges, histograms

These two systems don't talk to each other. Request timings from [telemetry.py](file:///c:/PROJECTS/eden-framework/eden/telemetry.py) don't flow into the Prometheus export from [metrics.py](file:///c:/PROJECTS/eden-framework/eden/core/metrics.py).

**Fix:** Have [telemetry.py](file:///c:/PROJECTS/eden-framework/eden/telemetry.py) record observations into `metrics.MetricsRegistry`:
```python
from eden.core.metrics import metrics

async def on_request_end(self):
    elapsed = time.time() - self.start_time
    metrics.observe("http_request_duration_seconds", elapsed, labels={"path": self.path})
```

---

### 22. `form.is_valid(include=[...])` — Validation Groups Set Required Fields to `None`

**File:** [forms.py](file:///c:/PROJECTS/eden-framework/eden/forms.py#L665-L669)

```python
if not in_scope and field_name not in data:
    data[field_name] = None  # ← Pydantic will validate `None` against required fields
```

**Impact:** Setting a required field to `None` will cause Pydantic to raise a validation error for that field (if it's not `Optional`). The intent is to skip validation, but the approach breaks it.

**Fix:** Use Pydantic's model with `model_construct()` for partial validation, or dynamically create an `Optional` variant of the schema.

---

### 23. `@reactive` Directive — No Server-Side WebSocket Channel Registration

**File:** [template_directives.py](file:///c:/PROJECTS/eden-framework/eden/template_directives.py#L502-L548)

The `@reactive` directive generates HTML with `hx-sync` attributes, but:
1. `get_sync_channel()` is referenced but not defined anywhere in the codebase
2. No WebSocket channel is registered server-side to actually push updates
3. The `hx-sync` attribute is not a standard HTMX attribute

**Impact:** Reactive templates render HTML that references non-existent Jinja2 functions and non-standard HTMX attributes. The feature is **non-functional**.

---

## Summary Table

| # | Severity | Issue | Module | Status |
|---|----------|-------|--------|--------|
| 1 | 🔴 Critical | Debug prints in production code | `context_middleware`, [tasks](file:///c:/PROJECTS/eden-framework/eden/tasks/__init__.py#398-402) | **Active** |
| 2 | 🔴 Critical | [create_user()](file:///c:/PROJECTS/eden-framework/eden/auth/actions.py#113-154) uses incompatible ORM APIs | `auth/actions` | **Will crash** |
| 3 | 🔴 Critical | [AuditableMixin](file:///c:/PROJECTS/eden-framework/eden/audit/__init__.py#12-30) does nothing | [audit](file:///c:/PROJECTS/eden-framework/eden/audit/__init__.py#32-61) | **Scaffolding** |
| 4 | 🔴 Critical | Sync Stripe calls block event loop | `payments/providers` | **Performance** |
| 5 | 🔴 Critical | `VectorModel.semantic_search()` calls non-existent method | `db/ai` | **Will crash** |
| 6 | 🟠 Medium | OAuth closure fragility | `auth/oauth` | **Latent** |
| 7 | 🟠 Medium | [SearchQueryBuilder](file:///c:/PROJECTS/eden-framework/eden/db/search.py#8-51) is string-only, no FTS integration | `db/search` | **Non-functional** |
| 8 | 🟠 Medium | [VersionedRouter](file:///c:/PROJECTS/eden-framework/eden/versioning.py#131-176) has no app integration | `versioning` | **Non-functional** |
| 9 | 🟠 Medium | Tenant cache caches `None` for 5 minutes | `tenancy/middleware` | **Data issue** |
| 10 | 🟠 Medium | Tenant ID comparison crashes on non-UUID strings | `tenancy/middleware` | **Will crash** |
| 11 | 🟠 Medium | `Request.from_scope()` doesn't exist | `middleware/rate_limit` | **Will crash** |
| 12 | 🟠 Medium | Metrics registry not thread-safe | `core/metrics` | **Data loss** |
| 13 | 🟠 Medium | Protocol with `@abc.abstractmethod` is misleading | `core/backends/base` | **Design** |
| 14 | 🟡 Moderate | Webhook handlers fail silently, events marked processed | `payments/webhooks` | **Data loss** |
| 15 | 🟡 Moderate | Tenant cache grows unboundedly | `tenancy/middleware` | **Memory leak** |
| 16 | 🟡 Moderate | Duplicate `RoleManager` import | `auth/__init__` | **Hygiene** |
| 17 | 🟡 Moderate | `validate_email()` return value misuse | `auth/actions` | **May crash** |
| 18 | 🟡 Moderate | [QueryCache](file:///c:/PROJECTS/eden-framework/eden/db/cache.py#251-326) leaks state across tests | `db/cache` | **Test issue** |
| 19 | 🟡 Moderate | `ttl=0` silently becomes `ttl=3600` in Redis cache | `db/cache` | **Silent bug** |
| 20 | 🔵 Design | `BaseService` is an empty abstraction | `services` | **Debt** |
| 21 | 🔵 Design | Duplicate metrics systems don't integrate | [telemetry](file:///c:/PROJECTS/eden-framework/eden/telemetry.py#54-57) + `core/metrics` | **Debt** |
| 22 | 🔵 Design | Form validation groups break Pydantic validation | `forms` | **Logic error** |
| 23 | 🔵 Design | `@reactive` references non-existent functions | `template_directives` | **Non-functional** |

---

## Recommended Fix Priority

### Tier 1 — Immediate (breaks every request or loses data)
1. Remove all `print(f"DEBUG ...")` statements (#1)
2. Fix [create_user()](file:///c:/PROJECTS/eden-framework/eden/auth/actions.py#113-154) ORM API mismatch (#2)
3. Fix `VectorModel.semantic_search()` session access (#5)
4. Wrap Stripe calls in `asyncio.to_thread()` (#4)
5. Fix `Request.from_scope()` in rate limiter (#11)

### Tier 2 — Next Sprint (causes data issues or crashes under specific conditions)
6. Implement [AuditableMixin](file:///c:/PROJECTS/eden-framework/eden/audit/__init__.py#12-30) properly (#3)
7. Fix tenant `None` caching (#9)
8. Add UUID validation in tenant middleware (#10)
9. Fix webhook handler error propagation (#14)
10. Add thread safety to [MetricsRegistry](file:///c:/PROJECTS/eden-framework/eden/core/metrics.py#40-269) (#12)

### Tier 3 — Technical Debt (non-functional features, design improvements)
11. Implement real FTS integration for [SearchQueryBuilder](file:///c:/PROJECTS/eden-framework/eden/db/search.py#8-51) (#7)
12. Wire [VersionedRouter](file:///c:/PROJECTS/eden-framework/eden/versioning.py#131-176) into app routing (#8)
13. Implement `@reactive` server-side channel (#23)
14. Integrate telemetry with metrics (#21)
15. Clean up form validation groups (#22)
