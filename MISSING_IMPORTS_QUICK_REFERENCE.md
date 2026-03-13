# Quick Reference: Missing/Incomplete Imports by File

## docs/getting-started/philosophy.md
- Line 89: DB query code missing `from eden.db import db`
- Line 147: `@app.get()` missing `from eden import Eden`
- Line 162: `Schema`, `field`, `EmailStr`, `field_validator` without imports - needs `from eden.forms import Schema, field, EmailStr` and `from pydantic import field_validator`
- Line 184: `@field_validator` missing import
- Line 199: `@app.post()` missing Eden import

## docs/getting-started/quickstart.md
- Line 9: Eden imports shown ✅ but later examples incomplete

## docs/getting-started/structure.md
- Line 87: `Router` used without import
- Line 106: `Resource`, `Model`, `Router`, `Schema` all missing imports
- Line 179: `User` model import missing in service layer code

## docs/getting-started/example-snippets.md
- Line 59-99: `Request` import missing in REST API example
- Line 100-133: Path parameters example missing imports
- Line 134-172: Authentication example missing `login_required` import
- Line 173-207: Templates example missing `render_template` import
- Line 208-231: Relationships example missing `ForeignKeyField` import
- Line 232-262: Query example missing `Q`, `F` imports
- Line 288-312: Error handling missing exception class imports
- Line 313-347: Background tasks missing task decorator import
- Line 429-461: Caching example missing `cache` import

## docs/guides/auth.md
- Line 13: `Role`, `RoleHierarchy` missing import
- Line 18: `roles_required`, `require_permission` decorators missing import
- Line 38: `OAuthManager`, `os` module context missing
- Line 65: `APIKey` class missing import
- Line 85: `RedirectResponse` missing import
- Line 129: `JWTProvider` missing import
- Line 169: `timedelta`, `datetime` missing import in session config
- Line 220: `LoginSchema` context missing, `@app.validate` decorator context
- Line 266: `require_permission` not imported clearly
- Line 327: `User` model import missing
- Line 350: `Session` class missing import
- Line 466: Middleware context missing
- Line 498: `send_email` function missing import
- Line 587: `generate_totp_secret`, `verify_totp` missing imports
- Line 615: `RateLimitMiddleware` missing import
- Line 685: `SocialAccount` model missing import

## docs/guides/advanced-routing.md
- Line 13: Router import context unclear in metadata example
- Line 44: `url_for` import not shown
- Line 90: `BaseHTTPMiddleware` missing import
- Line 104: Middleware class lacks proper imports
- Line 143: Route-specific middleware import missing
- Line 159: Conditional middleware example missing BaseHTTPMiddleware, JSONResponse
- Line 180: RBAC middleware missing BaseHTTPMiddleware, JSONResponse imports
- Line 197: ACL middleware missing Post model import, JSONResponse
- Line 226: Version management missing Router import
- Line 253: Sub-router pattern missing Router import
- Line 305: Route filtering missing JSONResponse
- Line 440: Sub-router organization missing Router import
- Line 483: Response handling missing JSONResponse, status imports
- Line 535: Error middleware missing Exception, JSONResponse imports
- Line 567: Testing pattern missing test client setup imports

## docs/guides/csrf-protection.md
- Line 62: `get_csrf_token` missing import
- Line 137: `get_csrf_token` missing import in token-based example
- Line 186: `verify_csrf_token` missing import
- Line 348: `user` context variable missing import
- Line 390: `user` context import missing
- Line 404: `app` context unclear
- Line 451: `csrf_exempt` decorator missing import
- Line 564: Status code constants missing import

## docs/guides/formfield-api.md
- Line 16: `FormField` context missing import of Schema or form instantiation
- Line 25: `BaseForm` class missing import
- Line 42: Schema, field imports missing in context
- Line 85: `@render_field` directive source unclear
- Line 208: Complete form example missing all necessary imports
- Line 274: `render_field_smart` function lacks context
- Line 304: Template function context missing

## docs/guides/caching.md
- Line 11: `cache` object import context unclear
- Line 35: `RedisCache` missing import
- Line 68: `@cache_view` decorator missing import
- Line 113: Pattern-clear Redis-only feature not explained
- Line 139: Caching decorator missing import or definition
- Line 151: Cache import context missing
- Line 195: `app.cache` usage assumes configuration context
- Line 365: Prometheus import missing
- Line 420: Version management imports missing

## docs/guides/admin.md
- Line 9: `admin` import source unclear
- Line 27: `@admin.register()` import context missing
- Line 47: `TabularInline` missing import
- Line 63: `@admin.action()` missing import
- Line 75: `AdminSite` missing import

## docs/guides/api.md
- Line 11: App decorator block missing `from eden import Eden`
- Line 50: `JSONResponse` missing import
- Line 80: Exception classes missing import
- Line 109: `Router` missing import in API versioning

## docs/guides/background-tasks.md
- Line 15: `create_broker` missing import
- Line 35: Task decorator context missing
- Line 76: Retry configuration missing import context

## docs/guides/components.md
- Line 13: Component imports incomplete in later examples
- Line 44: `@action` decorator missing import
- Line 113: `@component` directive source unclear

## docs/guides/dependencies.md
- Line 15: `Depends` import shown but context in usage missing

## docs/guides/core-app.md
- Line 55: `@app.on_startup` decorator context
- Line 79: `StripeClient` missing import

## docs/tutorial/task2_core.md
- Line 9: `setup_logging` missing import
- Line 55: Middleware context unclear on imports

## docs/tutorial/task3_orm.md
- Line 13: `from sqlalchemy.orm import Mapped` - shown separately but consistency unclear
- Line 105: `Q()` operator missing import
- Line 123: `User.DoesNotExist` exception source unclear
- Line 137: Transaction context manager import missing

## docs/tutorial/task4_routing.md
- Line 32: `Response`, `status` missing import
- Line 50: `Request` missing import
- Line 105: `BaseModel`, `EmailStr` missing import

## docs/tutorial/task5_templating.md
- Line 86: Template engine directives source unclear

## docs/tutorial/task6_forms.md
- Line 157: `@field_validator` missing import in code block

## docs/tutorial/task7_security.md
- Line 50: Router not defined in context
- Line 72: `Forbidden` exception missing import
- Line 126: Router not defined
- Line 169: Session configuration import missing
- Line 169: `hash_password`, `verify_password` missing import

## docs/tutorial/task8_saas.md
- Line 13: `admin` import missing
- Line 41: `stripe_client` missing import
- Line 55: `storage`, `S3StorageBackend` missing import
- Line 73: `stripe_webhook` missing import
- Line 135: `Tenant` model missing full definition
- Line 157: `record_metric` missing import
- Line 195: `StripeProvider` missing import

## docs/tutorial/task9_deployment.md
- Line 104: Context about container environment
- Line 220: Environment loading mechanism unclear

## docs/tutorial/task10_testing.md
- Line 39: `ASGITransport`, `AsyncClient` missing import
- Line 96: Schema import missing
- Line 136: Token generation context missing
- Line 187: Transaction import missing
- Line 241: Exception class imports missing

---

## Import Categories Summary

### Most Common Missing Imports:
1. **Eden Framework**:
   - `from eden import Eden, Router, Request, Response, status`
   - `from eden.auth import roles_required, login_required, etc.`
   - `from eden.forms import Schema, field, EmailStr`
   - `from eden.cache import cache, RedisCache, cache_view`
   
2. **Pydantic**:
   - `from pydantic import field_validator, BaseModel, EmailStr`
   
3. **Starlette/ASGI**:
   - `from starlette.responses import JSONResponse, RedirectResponse`
   - `from starlette.middleware.base import BaseHTTPMiddleware`
   
4. **SQLAlchemy**:
   - `from sqlalchemy.orm import Mapped, relationship`
   
5. **External Integrations**:
   - `from stripe import Stripe` / `from eden.payments import stripe_client`
   - `from redis import Redis` / `from eden.cache import RedisCache`

### Context Variables Without Clear Source:
- `user`, `request`, `app` - used without explicit imports
- `Model` base class - assumed available
- Field types - assumed available after one import

### Framework-Specific Issues:
- `@csrf`, `@render_field`, `@component`, `@url()` directives - source documentation unclear
- Template engine directives - which template engine? Jinja2 extended? Custom Eden directives?
- Decorators like `@field_validator`, `@action`, `@cache_view` - not always shown with imports
