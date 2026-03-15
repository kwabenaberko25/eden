Based on my comprehensive audit of the Eden Framework codebase, here are the significant architectural, design, and implementation issues I've found:

## 🔴 **CRITICAL ISSUES**

### 1. **Incomplete ORM Layer**

* **Session Management Chaos** : The QuerySet has fundamental session resolution issues. When a session is [_MISSING](vscode-file://vscode-app/c:/Users/COBBY/AppData/Local/Programs/Microsoft%20VS%20Code%20Insiders/4c822235d6/resources/app/out/vs/code/electron-browser/workbench/workbench.html), it throws [RuntimeError](vscode-file://vscode-app/c:/Users/COBBY/AppData/Local/Programs/Microsoft%20VS%20Code%20Insiders/4c822235d6/resources/app/out/vs/code/electron-browser/workbench/workbench.html) instead of auto-acquiring. This breaks the fluent API promise.
* **Auto-join Logic Fragile** : The [find_relationship_path()](vscode-file://vscode-app/c:/Users/COBBY/AppData/Local/Programs/Microsoft%20VS%20Code%20Insiders/4c822235d6/resources/app/out/vs/code/electron-browser/workbench/workbench.html) function will fail silently or crash on complex relationships (deep nesting, circular references, multiple paths).
* **Missing Relationship Inference** : `__pending_relationships__` and `__pending_m2m__` registries exist but it's unclear if they're actually being used to defer/resolve relationships.
* **No Transaction Isolation** : No built-in transaction handling, savepoints, or rollback mechanism exposed to users.

### 2. **Auth System Has Critical Gaps**

* **No First-Class User Model** : The framework references [BaseUser](vscode-file://vscode-app/c:/Users/COBBY/AppData/Local/Programs/Microsoft%20VS%20Code%20Insiders/4c822235d6/resources/app/out/vs/code/electron-browser/workbench/workbench.html) everywhere but it's never properly defined or exported. developers would have to create their own, losing framework integration.
* **Password Hashing Incomplete** : [hashers.py](vscode-file://vscode-app/c:/Users/COBBY/AppData/Local/Programs/Microsoft%20VS%20Code%20Insiders/4c822235d6/resources/app/out/vs/code/electron-browser/workbench/workbench.html) exists but no default hasher is configured. No argon2/bcrypt setup.
* **RBAC is Declarative Only** : The `__rbac__` dict can be set, but there's no enforcement at the query level—developers must manually apply security filters.
* **OAuth Stubs** : `oauth.py` and `providers.py` exist but are likely incomplete or placeholder implementations.
* **No Permission Middleware** : How does the framework know which user accessed what? No automatic binding.

### 3. **Templating Engine is Fragile**

* **Regex-Based Preprocessing** : The entire directive system (`@if`, `@for`, etc.) relies on regex substitution with manual protection blocks. This will:
* Break on edge cases (nested blocks, complex strings)
* Produce incorrect line numbers in error messages
* Fail on templates with certain character combinations
* **Protection Logic Incomplete** : The `protected_blocks` mechanism doesn't handle all cases (e.g., template literals, embedded JSON).
* **No AST Parsing** : A proper template engine would use AST parsing, not regex.

### 4. **Middleware Stack is Inconsistent**

* **Multiple CSRFMiddleware Implementations** : There's one in [middleware.py](vscode-file://vscode-app/c:/Users/COBBY/AppData/Local/Programs/Microsoft%20VS%20Code%20Insiders/4c822235d6/resources/app/out/vs/code/electron-browser/workbench/workbench.html) and another in [csrf.py](vscode-file://vscode-app/c:/Users/COBBY/AppData/Local/Programs/Microsoft%20VS%20Code%20Insiders/4c822235d6/resources/app/out/vs/code/electron-browser/workbench/workbench.html). They likely conflict.
* **No Middleware Ordering Guarantee** : The framework doesn't document or enforce middleware execution order (critical for security).
* **Session Not Properly Bound** : CSRF token lives in [request.session.eden_csrf_token](vscode-file://vscode-app/c:/Users/COBBY/AppData/Local/Programs/Microsoft%20VS%20Code%20Insiders/4c822235d6/resources/app/out/vs/code/electron-browser/workbench/workbench.html), but form directives reference [request.session.eden_csrf_token](vscode-file://vscode-app/c:/Users/COBBY/AppData/Local/Programs/Microsoft%20VS%20Code%20Insiders/4c822235d6/resources/app/out/vs/code/electron-browser/workbench/workbench.html). Inconsistent.

### 5. **Multi-Tenancy is Dangerous**

* **Schema Isolation Not Enforced** : The [TenantMiddleware](vscode-file://vscode-app/c:/Users/COBBY/AppData/Local/Programs/Microsoft%20VS%20Code%20Insiders/4c822235d6/resources/app/out/vs/code/electron-browser/workbench/workbench.html) sets context vars but doesn't enforce them in queries. A developer could accidentally query tenant A's data while tenant B is active.
* **No Query Interception** : The QuerySet doesn't automatically add tenant filters based on `get_current_tenant_id()`.
* **Raw SQL Bypass** : [raw_sql.py](vscode-file://vscode-app/c:/Users/COBBY/AppData/Local/Programs/Microsoft%20VS%20Code%20Insiders/4c822235d6/resources/app/out/vs/code/electron-browser/workbench/workbench.html) exists—developers can write raw SQL and bypass all tenant isolation.
* **Schema Provisioning Incomplete** : `Tenant.provision_schema()` tries to use unbound methods like [Model._db.set_schema()](vscode-file://vscode-app/c:/Users/COBBY/AppData/Local/Programs/Microsoft%20VS%20Code%20Insiders/4c822235d6/resources/app/out/vs/code/electron-browser/workbench/workbench.html) which likely don't exist.

### 6. **Dependency Injection is Incomplete**

* **No Context Manager Support** : DependencyResolver exists but doesn't mention how it handles cleanup for generator deps.
* **Circular Dependency Detection Missing** : No check for circular deps.
* **No Lazy Loading** : All deps are eagerly resolved.
* **Type Coercion Broken** : The docstring says "Attempt type coercion based on annotation" but the code is cut off.

---

## ⚠️ **MAJOR ARCHITECTURAL PROBLEMS**

### 7. **WebSocket Layer is Duplicated & Confused**

* **Two WebSocket Modules** : Both [websocket.py](vscode-file://vscode-app/c:/Users/COBBY/AppData/Local/Programs/Microsoft%20VS%20Code%20Insiders/4c822235d6/resources/app/out/vs/code/electron-browser/workbench/workbench.html) and [__init__.py](vscode-file://vscode-app/c:/Users/COBBY/AppData/Local/Programs/Microsoft%20VS%20Code%20Insiders/4c822235d6/resources/app/out/vs/code/electron-browser/workbench/workbench.html) exist with conflicting implementations.
* **Connection State Management Broken** : The [__init__.py](vscode-file://vscode-app/c:/Users/COBBY/AppData/Local/Programs/Microsoft%20VS%20Code%20Insiders/4c822235d6/resources/app/out/vs/code/electron-browser/workbench/workbench.html) tries to dynamically import from the parent module using file paths and `importlib`—this is fragile and breaks packaging.
* **No Automatic Auth** : WebSocket connections have no built-in user authentication or isolation.
* **ConnectionManager / RealTimeManager** : Two separate implementations doing slightly different things. Which one should I use?

### 8. **Realtime Features Not Integrated**

* [realtime.py](vscode-file://vscode-app/c:/Users/COBBY/AppData/Local/Programs/Microsoft%20VS%20Code%20Insiders/4c822235d6/resources/app/out/vs/code/electron-browser/workbench/workbench.html) exists with a standalone `RealTimeManager`, but there's no integration with:
  * Context tenants
  * User authentication
  * Message system
* **Broadcast Without Permission** : Anyone can broadcast to any channel.

### 9. **Component System Incomplete**

* **Components Can't Be Passed Data** : The `Component.get_context_data()` method is defined but examples show no way to pass reactive state.
* **No Action Dispatch** : Components have `@register` and `_action_registry` but no clear way to trigger actions from templates or handle responses.
* **Jinja Integration Missing** : The `ComponentExtension` is mentioned but not implemented in the codebase I reviewed.

### 10. **Tasks/Scheduler Are Stubs**

* **Taskiq Wrapper is Thin** : [EdenBroker](vscode-file://vscode-app/c:/Users/COBBY/AppData/Local/Programs/Microsoft%20VS%20Code%20Insiders/4c822235d6/resources/app/out/vs/code/electron-browser/workbench/workbench.html) wraps taskiq but adds little value.
* **Periodic Tasks Don't Start** : `PeriodicTask.start()` exists but it's unclear if it's ever called. [app.on_startup](vscode-file://vscode-app/c:/Users/COBBY/AppData/Local/Programs/Microsoft%20VS%20Code%20Insiders/4c822235d6/resources/app/out/vs/code/electron-browser/workbench/workbench.html) hookups are missing.
* **Cron Expression Parser Incomplete** : The scheduler has began parsing but doesn't integrate with a cron scheduler (no croniter/APScheduler).
* **No Error Recovery** : Task failures are only logged, not retried or persisted.

### 11. **Payments Module is Skeleton**

* **Webhook Verification Incomplete** : `StripeProvider.verify_webhook_signature()` interface exists but implementation is cut off.
* **No Error Scenarios** : No handling for failed charges, chargeback disputes, etc.
* **No Idempotency** : Webhook events aren't deduplicated—if the same event is received twice, it will process twice.

### 12. **Storage Backends Have Consistency Issues**

* **No Atomic Uploads** : File is uploaded to S3 but if the DB save fails, the file is orphaned.
* **No Cleanup** : Deleted files aren't automatically removed from S3.
* **No Progress Tracking** : Large file uploads have no progress callbacks.
* **Supabase Backend is Incomplete** : Uses sync client initialization in an async context.

### 13. **Error Handling is Inconsistent**

* **No Global Error Handler Hook** : Exception handlers are registered per-exception type but there's no way to customize error pages globally.
* **Admin Panel Error Routes Hardcoded** : The admin views call `_check_staff()` which returns JSON but doesn't emit proper error responses.
* **Blank Error Messages** : `exception.py` has placeholders like [detail = &#34;An unexpected error occurred.&#34;](vscode-file://vscode-app/c:/Users/COBBY/AppData/Local/Programs/Microsoft%20VS%20Code%20Insiders/4c822235d6/resources/app/out/vs/code/electron-browser/workbench/workbench.html) without context about what actually failed.

---

## 🟠 **DESIGN & ORGANIZATION ISSUES**

### 14. **No Clear Async Context Propagation**

* **ContextVars Used Everywhere** : `set_app()`, [set_user()](vscode-file://vscode-app/c:/Users/COBBY/AppData/Local/Programs/Microsoft%20VS%20Code%20Insiders/4c822235d6/resources/app/out/vs/code/electron-browser/workbench/workbench.html), `set_current_tenant()` all use ContextVars but there's no guarantee they're set/reset consistently.
* **No Cleanup** : No automatic reset of context on request end.
* **No Request Lifecycle Hooks** : Where should middleware set these? App startup? Per-request in ASGI middleware?

### 15. **Configuration is Ad-Hoc**

* **No Config Object** : Settings are scattered across [app.state](vscode-file://vscode-app/c:/Users/COBBY/AppData/Local/Programs/Microsoft%20VS%20Code%20Insiders/4c822235d6/resources/app/out/vs/code/electron-browser/workbench/workbench.html), environment variables, and hardcoded defaults.
* **No Validation** : No schema for required vs. optional config.
* **No Secrets Management** : How do I safely set Stripe keys, database URLs, etc.?
* **No Environment Support** : No `.env` file loading, no dev/prod config switching.

### 16. **Testing Infrastructure is Missing**

* **No TestClient** : No built-in test helpers like `TestClient` from Starlette.
* **No Fixtures** : No fixtures for common objects (users, models, request contexts).
* **No pytest Plugins** : No Eden-specific pytest integration.
* **Mocking is Manual** : Examples show [from unittest.mock import MagicMock](vscode-file://vscode-app/c:/Users/COBBY/AppData/Local/Programs/Microsoft%20VS%20Code%20Insiders/4c822235d6/resources/app/out/vs/code/electron-browser/workbench/workbench.html)—not scalable.

### 17. **Type Hints are Incomplete**

* **Generic Types Inconsistent** : Some functions use [type[T]](vscode-file://vscode-app/c:/Users/COBBY/AppData/Local/Programs/Microsoft%20VS%20Code%20Insiders/4c822235d6/resources/app/out/vs/code/electron-browser/workbench/workbench.html) properly, others use [Any](vscode-file://vscode-app/c:/Users/COBBY/AppData/Local/Programs/Microsoft%20VS%20Code%20Insiders/4c822235d6/resources/app/out/vs/code/electron-browser/workbench/workbench.html).
* **Return Types Missing** : Many async functions don't declare return types.
* **Optional Not Used** : [request: Request | None](vscode-file://vscode-app/c:/Users/COBBY/AppData/Local/Programs/Microsoft%20VS%20Code%20Insiders/4c822235d6/resources/app/out/vs/code/electron-browser/workbench/workbench.html) should be [request: Request | None = None](vscode-file://vscode-app/c:/Users/COBBY/AppData/Local/Programs/Microsoft%20VS%20Code%20Insiders/4c822235d6/resources/app/out/vs/code/electron-browser/workbench/workbench.html) to be clear about defaults.
* **TYPE_CHECKING Abuse** : Some imports are only under [TYPE_CHECKING](vscode-file://vscode-app/c:/Users/COBBY/AppData/Local/Programs/Microsoft%20VS%20Code%20Insiders/4c822235d6/resources/app/out/vs/code/electron-browser/workbench/workbench.html) but they're used in runtime code.

### 18. **Logging is Not Structured**

* **Request ID Correlation Missing** : The `EdenFormatter` references `request_id` but nothing sets it.
* **No Log Level Configuration Per Module** : Only root logger is configured.
* **Error Logging Incomplete** : Exceptions are logged but stack traces aren't always included.

### 19. **Migrations Don't Exist**

* **No Alembic Integration** : [MigrationManager](vscode-file://vscode-app/c:/Users/COBBY/AppData/Local/Programs/Microsoft%20VS%20Code%20Insiders/4c822235d6/resources/app/out/vs/code/electron-browser/workbench/workbench.html) is imported but not implemented.
* **No Version Tracking** : How do I track schema changes across deploys?
* **No Rollback Support** : How do I revert a migration?

### 20. **Admin Panel is Too Simple**

* **No Field Widgets** : Text fields, dates, relationships all render as generic inputs.
* **No Custom Actions** : Can't add bulk actions, exports, or custom buttons.
* **No Audit Trail** : No tracking who changed what.
* **List Display is Hardcoded** : Auto-detection picks arbitrary fields and breaks on relationships.

---

## 🔵 **MISSING FEATURES**

### 21. **No Database Transactions Exposed**

* No `@atomic` decorator or `async with db.transaction():`
* No isolation level configuration

### 22. **No Query Result Caching**

* [cache](vscode-file://vscode-app/c:/Users/COBBY/AppData/Local/Programs/Microsoft%20VS%20Code%20Insiders/4c822235d6/resources/app/out/vs/code/electron-browser/workbench/workbench.html) exists but it's not integrated with QuerySet

### 23. **No Slugfield or Auto-Slug Generation**

* Common Django pattern, missing here

### 24. **No Celery/Celery Alternative Integration**

* [tasks.py](vscode-file://vscode-app/c:/Users/COBBY/AppData/Local/Programs/Microsoft%20VS%20Code%20Insiders/4c822235d6/resources/app/out/vs/code/electron-browser/workbench/workbench.html) wraps taskiq but no background worker setup docs

### 25. **No Rate Limiting**

* [middleware.py](vscode-file://vscode-app/c:/Users/COBBY/AppData/Local/Programs/Microsoft%20VS%20Code%20Insiders/4c822235d6/resources/app/out/vs/code/electron-browser/workbench/workbench.html) mentions "rate limiting" but no implementation

### 26. **No API Versioning Support**

* How do I support `/v1/` and `/v2/` endpoints?

### 27. **No Request/Response Middleware for Auto Serialization**

* Developers must manually [JsonResponse(model)](vscode-file://vscode-app/c:/Users/COBBY/AppData/Local/Programs/Microsoft%20VS%20Code%20Insiders/4c822235d6/resources/app/out/vs/code/electron-browser/workbench/workbench.html)

### 28. **No Built-in Pagination Links**

* [Page](vscode-file://vscode-app/c:/Users/COBBY/AppData/Local/Programs/Microsoft%20VS%20Code%20Insiders/4c822235d6/resources/app/out/vs/code/electron-browser/workbench/workbench.html) class exists but doesn't generate [?page=X](vscode-file://vscode-app/c:/Users/COBBY/AppData/Local/Programs/Microsoft%20VS%20Code%20Insiders/4c822235d6/resources/app/out/vs/code/electron-browser/workbench/workbench.html) links

---

## 🟡 **CONSISTENCY & CORRECTNESS ISSUES**

### 29. **String Field Default Max Length is Arbitrary**

* [StringField()](vscode-file://vscode-app/c:/Users/COBBY/AppData/Local/Programs/Microsoft%20VS%20Code%20Insiders/4c822235d6/resources/app/out/vs/code/electron-browser/workbench/workbench.html) defaults to 255, but database maximums vary by vendor

### 30. **UUID vs String ID Inconsistency**

* Some models use [uuid.UUID](vscode-file://vscode-app/c:/Users/COBBY/AppData/Local/Programs/Microsoft%20VS%20Code%20Insiders/4c822235d6/resources/app/out/vs/code/electron-browser/workbench/workbench.html), others likely use integer IDs
* No convention documented

### 31. **Datetime Handling Incomplete**

* No timezone awareness guidelines
* [datetime: datetime = DateTimeField()](vscode-file://vscode-app/c:/Users/COBBY/AppData/Local/Programs/Microsoft%20VS%20Code%20Insiders/4c822235d6/resources/app/out/vs/code/electron-browser/workbench/workbench.html) but should it auto-default to [func.now()](vscode-file://vscode-app/c:/Users/COBBY/AppData/Local/Programs/Microsoft%20VS%20Code%20Insiders/4c822235d6/resources/app/out/vs/code/electron-browser/workbench/workbench.html)?

### 32. **Email Validation is Weak**

* Regex-based email validation in [validators.py](vscode-file://vscode-app/c:/Users/COBBY/AppData/Local/Programs/Microsoft%20VS%20Code%20Insiders/4c822235d6/resources/app/out/vs/code/electron-browser/workbench/workbench.html) won't catch all invalid emails
* No domain DNS validation
* No confirmation email flow (built-in)

### 33. **File Uploads Not Validated**

* No max file size checks
* No file type whitelist validation
* No virus scanning integration

### 34. **SQL Injection Risks in Raw SQL**

* [raw_sql.py](vscode-file://vscode-app/c:/Users/COBBY/AppData/Local/Programs/Microsoft%20VS%20Code%20Insiders/4c822235d6/resources/app/out/vs/code/electron-browser/workbench/workbench.html) allows raw strings. Developers must use parameterization manually.
* No warnings or safety checks

### 35. **LIKE Wildcard Injection in Queries**

* The [parse_lookups](vscode-file://vscode-app/c:/Users/COBBY/AppData/Local/Programs/Microsoft%20VS%20Code%20Insiders/4c822235d6/resources/app/out/vs/code/electron-browser/workbench/workbench.html) function doesn't escape `%` and `_` in ILIKE/CONTAINS lookups
* [name__icontains=&#34;100%&#34;](vscode-file://vscode-app/c:/Users/COBBY/AppData/Local/Programs/Microsoft%20VS%20Code%20Insiders/4c822235d6/resources/app/out/vs/code/electron-browser/workbench/workbench.html) will match "1001", "1002", etc. unintentionally

---

## 📋 **API INCONSISTENCIES**

### 36. **ORM Methods Don't Match Django Conventions**

* []()
* []()
* []()
* []()

### 37. **Dependency Injection Syntax is Unclear**

* [Depends()](vscode-file://vscode-app/c:/Users/COBBY/AppData/Local/Programs/Microsoft%20VS%20Code%20Insiders/4c822235d6/resources/app/out/vs/code/electron-browser/workbench/workbench.html) exists but examples don't show all use cases
* How do I inject the app itself?
* How do I inject current_user?

### 38. **Template Rendering Function Inconsistent**

* `render_template()` vs [request.render()](vscode-file://vscode-app/c:/Users/COBBY/AppData/Local/Programs/Microsoft%20VS%20Code%20Insiders/4c822235d6/resources/app/out/vs/code/electron-browser/workbench/workbench.html)
* Which should I use?

### 39. **Error Response Format Inconsistent**

* Some use `ErrorResponse`, some use [JsonResponse](vscode-file://vscode-app/c:/Users/COBBY/AppData/Local/Programs/Microsoft%20VS%20Code%20Insiders/4c822235d6/resources/app/out/vs/code/electron-browser/workbench/workbench.html) with [error: true](vscode-file://vscode-app/c:/Users/COBBY/AppData/Local/Programs/Microsoft%20VS%20Code%20Insiders/4c822235d6/resources/app/out/vs/code/electron-browser/workbench/workbench.html)
* No OpenAPI schema generation

### 40. **Model Inheritance Broken**

* `__abstract__ = True` works but multi-table inheritance isn't mentioned
* Mixin inheritance unclear (SoftDeleteMixin added manually?)

---

## 📚 **DOCUMENTATION & EXAMPLES ISSUES**

### 41. **README Makes Claims That Aren't Implemented**

* "Zero-Config ORM" — config is everywhere
* "Native Multi-Tenancy" — not enforced at query level
* "Built-in Security" — CSRF has multiple implementations

### 42. **Example Code is Incomplete**

* `04_authentication.py` references `login_required` decorator that doesn't exist
* [IntField](vscode-file://vscode-app/c:/Users/COBBY/AppData/Local/Programs/Microsoft%20VS%20Code%20Insiders/4c822235d6/resources/app/out/vs/code/electron-browser/workbench/workbench.html) used but never imported
* `render_template()` used but not shown where it comes from

### 43. **No Getting Started Tutorial**

* Quickstart is 10 lines, doesn't show:
  * How to create a model
  * How to run migrations
  * How to define routes
  * How to handle requests/responses

### 44. **Docstrings Have Placeholder Content**

* Many functions have "..." blocks instead of actual implementation

---

## 🎯 **SUMMARY OF META-ISSUES**

1. **The framework is trying to do too much** (ORM, auth, templates, realtime, payments, storage, admin) but most layers are incomplete.
2. **Architecture is inconsistent** :

* Sometimes follows Django patterns, sometimes FastAPI
* Session management is confusing (auto-inject vs manual)
* Module organization has duplication (websocket, csrf, etc.)

1. **Security is ad-hoc** :

* Tenant isolation not enforced
* CSRF has multiple implementations
* SQL injection risks in raw queries
* Wildcard injection in LIKE queries
* File upload validation missing

1. **Testing is critical and missing** :

* No test client
* No test database
* Hard to mock dependencies

1. **Configuration is dangerous** :

* Secrets in code or unvalidated env vars
* No defaults that work for dev/prod
* No configuration schema

1. **Type hints are incomplete** , making IDE support poor and runtime errors likely.
2. **Key integrations are stubs** :

* Payments (SDK calls cut off)
* Migrations (no Alembic hookup)
* Background tasks (taskiq wrapper doesn't start workers)

1. **Performance is not addressed** :

* No connection pooling docs
* No query optimization (N+1 queries possible)
* Cache system exists but isn't integrated

---

### **My Recommendation** : Focus on 3–5 core areas and finish them completely before expanding further:

1. ✅ **Database Layer** — Complete ORM with full transaction support, migrations, and indexed queries
2. ✅ **Authentication** — Build a complete auth system with password hashing, RBAC, OAuth redirects
3. ✅ **Templating** — Replace regex preprocessor with proper AST parser
4. ✅ ** Tenancy** — Enforce tenant isolation at the ORM level automatically
5. ✅ **Error Handling** — Unified exception handling with proper error pages and logging

Everything else (payments, components, admin) should be documented with clear extension points so users can plug in their own solutions.
