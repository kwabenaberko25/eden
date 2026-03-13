# Documentation Missing Imports Audit Report

Comprehensive analysis of all Python code blocks in docs/ that have missing or incomplete imports.

---

## Summary Statistics
- **Total Files Checked**: 32 markdown files
- **Files with Issues**: 28
- **Total Issues Found**: 95+

---

## Critical Issues (Block Entire Example)

### docs/getting-started/philosophy.md
- **Line 89**: Code block using `db.query()` with no imports shown
  - Missing: `from eden.db import db` or equivalent
  - Example: `def get_data(): return db.query(...)`

- **Line 147**: `@app.get()` decorator without imports
  - Missing: `from eden import Eden` at start
  
- **Line 162**: Uses `Schema`, `field`, `EmailStr`, `field_validator` without imports
  - Missing: `from eden.forms import Schema, field, EmailStr` and `from pydantic import field_validator`
  - Code snippet assumes these are magically available

- **Line 184**: `@field_validator` decorator without the import shown
  - Missing: `from pydantic import field_validator`

- **Line 199**: `@app.post()` without Eden import
  - Missing: `from eden import Eden`

- **Line 162**: `User.create_from(credentials)` without importing or explaining User model
  - Missing: `from app.models import User` or clarification on where User comes from

### docs/getting-started/quickstart.md
- **Line 9**: Missing imports for `Eden, Model, StringField, BoolField, Request`
  - Shown: `from eden import Eden, Model, StringField, BoolField, Request` ✅
  - Missing from later examples: `Task.create()` assumes Model is imported

- **Line 49**: `Task.create()` and `Task.all()` used without explaining where Task comes from
  - Missing: Context that Task extends Model

- **Line 285**: Template rendering uses `render_template` but first code block shows `request.render()`
  - Missing clarification on import difference

- **Line 360**: Form validation assumes knowledge of `UserSchema` 
  - Missing: Show the import and minimal schema definition

### docs/getting-started/structure.md
- **Line 87**: `Router` used without import
  - Missing: `from eden import Router` at the start of the code block

- **Line 106**: `Resource`, `Model`, `Router`, `Schema` all used without imports
  - Missing: All four imports needed

- **Line 179**: Service layer code uses `User` without import
  - Missing: `from app.models import User`

- **Line 196**: Service class without showing imports for methods used

---

## Guides Issues

### docs/guides/auth.md

- **Line 13**: Role hierarchy code block
  - Missing: `from eden.auth import Role, RoleHierarchy`
  - Code: `hierarchy = RoleHierarchy({...})`

- **Line 18**: `@roles_required` decorator
  - Missing: `from eden.auth import roles_required, require_permission`
  - Code: `@roles_required(["admin"])`

- **Line 38**: OAuth setup with `OAuthManager`
  - Missing: `import os`, `from eden.auth.oauth import OAuthManager`
  - Uses: `os.getenv()`, `OAuthManager()`

- **Line 65**: `APIKey.generate()` without showing import
  - Missing: `from eden import APIKey` or `from eden.auth import APIKey`

- **Line 85**: `RedirectResponse` in OAuth callback
  - Missing: `from starlette.responses import RedirectResponse`

- **Line 129**: JWT setup uses `JWTProvider` 
  - Missing: `from eden.auth.providers import JWTProvider`

- **Line 169**: Session configuration uses `timedelta`, `datetime`
  - Missing: `from datetime import timedelta, datetime`

- **Line 220**: `@app.validate` decorator
  - Missing: `from eden import app` or proper context
  - Also uses `LoginSchema` without import

- **Line 266**: RBAC middleware example uses `require_permission`
  - Missing: Import not shown at code block start

- **Line 288**: `hasher` usage without explaining where it comes from
  - Missing: Clarification on password hashing module

- **Line 327**: `User` model usage
  - Missing: `from app.models import User`

- **Line 350**: Session management code
  - Missing: `from eden.auth import Session`

- **Line 376**: `verify_password()` without context
  - Missing: Explanation that this comes from User model

- **Line 466**: RBAC middleware `@app.middleware`
  - Missing: Context about where middleware is defined

- **Line 498**: `send_email` function
  - Missing: `from eden import send_email`

- **Line 543**: Email template context
  - Missing: Clarification on where template directory is

- **Line 587**: Two-factor authentication setup
  - Missing: `from eden.auth import generate_totp_secret, verify_totp`

- **Line 615**: Rate limiting configuration
  - Missing: `from eden.middleware import RateLimitMiddleware`

- **Line 685**: Social account management
  - Missing: `from eden.auth.social import SocialAccount`

---

### docs/guides/advanced-routing.md

- **Line 13**: Metadata decorator without import context
  - Missing: `from eden import Router`

- **Line 44**: Named routes and URL building
  - Missing: `from eden.routing import url_for` at the code block start

- **Line 64**: `Router` initialization
  - Missing: Import shown in context

- **Line 90**: Middleware example with `RequireAuth()`
  - Missing: `from starlette.middleware.base import BaseHTTPMiddleware`

- **Line 104**: Custom middleware class definition
  - Missing: BaseHTTPMiddleware import, Request import

- **Line 131**: Template URL generation
  - Missing: Explanation of `@url_for` source

- **Line 143**: Route-specific middleware application
  - Missing: Middleware import

- **Line 159**: Conditional middleware example
  - Missing: All imports for BaseHTTPMiddleware, JSONResponse

- **Line 180**: RBAC middleware
  - Missing: Import statements, JSONResponse from starlette

- **Line 197**: Resource ACL middleware
  - Missing: Post model import, JSONResponse

- **Line 226**: Version management with routers
  - Missing: Router import

- **Line 253**: Sub-router inclusion pattern
  - Missing: Router import

- **Line 276**: OpenAPI documentation configuration
  - Missing: Show where these parameters come from

- **Line 305**: Documentation from docstrings
  - Missing: Context about how Eden parses these

- **Line 348**: Route filtering in schema
  - Missing: JSONResponse, schema imports

- **Line 393**: Complex route patterns
  - Missing: Import context

- **Line 440**: Sub-router organization
  - Missing: Router import

- **Line 483**: Response handling
  - Missing: JSONResponse, status imports

- **Line 535**: Error handling middleware
  - Missing: Exception, JSONResponse imports

- **Line 567**: Testing with named routes
  - Missing: Test client setup, pytest fixture imports

- **Line 582**: Reverse URL generation patterns
  - Missing: url_for import

---

### docs/guides/csrf-protection.md

- **Line 62**: `get_csrf_token()` function
  - Missing: `from eden.security.csrf import get_csrf_token`
  - Code: `csrf_token = get_csrf_token(request)`

- **Line 137**: Signed token usage with `get_csrf_token`
  - Missing: Import not shown

- **Line 186**: `verify_csrf_token()` function
  - Missing: `from eden.security.csrf import verify_csrf_token`

- **Line 226**: Session-less CSRF handling
  - Missing: Import context

- **Line 259**: AJAX token extraction
  - Missing: `document` object context (client-side code shown without JS context)

- **Line 303**: Mobile app CSRF example
  - Missing: `fetch()` in JavaScript context (mixing Python/JS without clear separation)

- **Line 348**: `user` context variable
  - Missing: `from eden.context import user` import

- **Line 390**: Hybrid checkout flow
  - Missing: `user` context import

- **Line 404**: Middleware exclusion configuration
  - Missing: Where `app` comes from in context

- **Line 426**: `exclude_paths` middleware option
  - Missing: Documentation reference

- **Line 451**: `csrf_exempt` decorator
  - Missing: `from eden import csrf_exempt` or similar

- **Line 499**: Custom CSRF error handler
  - Missing: Decorator and import context

- **Line 512**: Token validation in middleware
  - Missing: Where CSRFMiddleware is imported from

- **Line 551**: Webhook CSRF handling
  - Missing: Explanation of external API context

- **Line 564**: Status code constants
  - Missing: `from eden import status` or `from starlette import status`

- **Line 581**: Form data parsing
  - Missing: `request.form()` async context

---

### docs/guides/formfield-api.md

- **Line 16**: `FormField` methods without showing how to get form object
  - Missing: `form = UserSchema.as_form()` import context

- **Line 25**: `BaseForm.from_request()` 
  - Missing: `from eden.forms import BaseForm`

- **Line 32**: Form rendering in templates
  - Missing: Context about where form comes from (should be passed in context)

- **Line 42**: Custom rendering without showing Schema import
  - Missing: `from eden.forms import Schema, field`

- **Line 51**: Widget methods without imports
  - Missing: Implied that these are methods on FormField

- **Line 58**: Complete example using form fields
  - Missing: Imports for Schema, field, and form rendering functions

- **Line 67**: Conditional rendering with form state
  - Missing: How to get form.errors

- **Line 74**: Fluent method chaining
  - Missing: Demonstration that FormField is returned from schema.as_form()

- **Line 85**: Template-side rendering
  - Missing: Clarification on `@render_field` directive source

- **Line 96**: Error styling
  - Missing: Where form['field_name'] comes from after validation

- **Line 105**: Form validation errors
  - Missing: Validation error import context

- **Line 123**: Widget type selection
  - Missing: How widget types are chosen/configured

- **Line 135**: Render method parameters
  - Missing: Where render() method is called from

- **Line 154**: Label rendering
  - Missing: Where render_label() comes from

- **Line 172**: Select widget with choices
  - Missing: How choices parameter is formatted

- **Line 183**: File upload widget
  - Missing: File handling import context

- **Line 208**: Complete form example
  - Missing: Imports for all classes and functions used

- **Line 274**: Smart field rendering function
  - Missing: Function definition context, return types

- **Line 304**: Template integration
  - Missing: Where render_field_smart comes from

- **Line 346**: Conditional attributes
  - Missing: How to conditionally disable/enable fields

- **Line 375**: Fluent chain examples heading section
  - Missing: No imports shown for this section

- **Line 389**: Form builder patterns
  - Missing: Complete import example

---

### docs/guides/caching.md

- **Line 11**: `from eden.cache import cache` - but where does `cache` come from?
  - Issue: Code shows `await cache.set()` but doesn't explain initialization

- **Line 35**: `RedisCache` without imports
  - Missing: `from eden.cache import RedisCache`

- **Line 68**: `@cache_view` decorator
  - Missing: Decorator import not shown

- **Line 93**: Cache method reference section
  - Missing: Which cache backend these methods apply to

- **Line 113**: Pattern-based clearing
  - Missing: Explanation that this is Redis-only feature

- **Line 139**: Decorator-based caching
  - Missing: Custom decorator definition or import

- **Line 151**: Query result caching
  - Missing: Import context for cache

- **Line 161**: Helper function pattern
  - Missing: Definition of cache variable or decorator

- **Line 174**: Cache key construction
  - Missing: Where f"..." string templates come from

- **Line 195**: Distributed caching
  - Missing: `await app.cache.set()` assumes app.cache is configured

- **Line 221**: Cache statistics/metrics
  - Missing: Where metrics tracking comes from

- **Line 237**: View cache invalidation
  - Missing: Pattern for constructing cache keys to clear

- **Line 265**: Cache headers middleware
  - Missing: Import context

- **Line 285**: Cache decorator with variations
  - Missing: Show all available decorator options/imports

- **Line 316**: Conditional caching
  - Missing: Import context

- **Line 332**: Cache warming patterns
  - Missing: Background task setup

- **Line 365**: Cache metrics export
  - Missing: Prometheus client library import

- **Line 380**: Cache performance monitoring
  - Missing: Timing decorator or context manager imports

- **Line 401**: Per-user caching
  - Missing: Where request.user comes from

- **Line 410**: Cache busting strategies
  - Missing: Event listener pattern imports

- **Line 420**: Cache versioning
  - Missing: Version management strategy imports

- **Line 458**: Advanced cache patterns
  - Missing: Context and imports for all patterns shown

---

### docs/guides/admin.md

- **Line 9**: `from eden.admin import admin` - but `admin` is used as decorator
  - Issue: Unclear if this is the right module

- **Line 27**: `@admin.register()` decorator
  - Missing: Full admin import context

- **Line 47**: `admin.TabularInline`
  - Missing: Full import

- **Line 63**: `@admin.action()` decorator
  - Missing: Import context

- **Line 75**: `admin.AdminSite` class
  - Missing: Import context

---

### docs/guides/api.md

- **Line 11**: First code block with decorators missing app import
  - Missing: `from eden import Eden; app = Eden(...)`

- **Line 50**: Code block using `JSONResponse` without import
  - Missing: `from starlette.responses import JSONResponse` or `from eden import JSONResponse`

- **Line 80**: Error handling with exceptions
  - Missing: `from eden.exceptions import ValidationError, PermissionDenied`

- **Line 109**: API versioning with routers
  - Missing: `from eden import Router`

- **Line 129**: Pagination code
  - Missing: Context about Post model and where it comes from

---

### docs/guides/background-tasks.md

- **Line 15**: `create_broker()` function
  - Missing: `from eden.tasks import create_broker`

- **Line 35**: Task decorator usage
  - Missing: Where `app.broker()` comes from

- **Line 50**: `.kiq()` method
  - Missing: Explanation of where this method comes from

- **Line 76**: Task retry configuration
  - Missing: Import context

- **Line 105**: Periodic tasks with `.every()`
  - Missing: Where `.every()` method comes from

---

### docs/guides/components.md

- **Line 13**: `from eden.components import Component, register`
  - Missing: But code in next block doesn't show decorator or all needed imports

- **Line 44**: Component actions with `@action` decorator
  - Missing: `from eden.components import action`

- **Line 113**: `@component` directive in template
  - Missing: This is a template directive - unclear how it's defined

- **Line 126**: `@url()` template directive
  - Missing: Explanation of this directive source

---

### docs/guides/dependencies.md

- **Line 15**: `from eden.dependencies import Depends`
  - Missing: But used as function parameter without showing import in context

- **Line 33**: Parametrized dependencies
  - Missing: Pagination helper definition context

- **Line 56**: Dependency caching pattern
  - Missing: Import context

---

### docs/guides/core-app.md

- **Line 9**: `from eden import Eden` shown
  - Missing: In advanced section - `@app.on_startup` doesn't show import context

- **Line 55**: Lifecycle hooks without imports
  - Missing: Decorator source

- **Line 66**: `app.state` usage
  - Missing: Context about thread-safety guarantees

- **Line 79**: `StripeClient` example without import
  - Missing: `from stripe import Stripe` or Eden's stripe integration

- **Line 99**: Request handler without proper imports
  - Missing: app.state context

---

## Tutorial Issues

### docs/tutorial/task2_core.md

- **Line 9**: `setup_logging()` used without showing where it comes from
  - Missing: `from eden import setup_logging`

- **Line 55**: Middleware setup without showing import context
  - Missing: Confirm Eden is imported at the start of the file

- **Line 66**: `app.include_router()` assuming Eden instance
  - Missing: Show full context

### docs/tutorial/task3_orm.md

- **Line 13**: `from eden.db import Model, f` - shown ✅
  - Missing: `from sqlalchemy.orm import Mapped` is shown separately but not together

- **Line 35**: `relationship()` function
  - Missing: `from sqlalchemy.orm import relationship` shown but could be clearer

- **Line 62**: `Post.filter()` usage
  - Missing: Context about chaining

- **Line 93**: `select_related()` method
  - Missing: Import context

- **Line 105**: Complex filter with `Q()` operator
  - Missing: `from eden.db import Q` or equivalent

- **Line 123**: Try/except error handling
  - Missing: What exception is `User.DoesNotExist`?

- **Line 137**: Transaction usage
  - Missing: `async with db.transaction():`

- **Line 148**: Migration command
  - Missing: Explanation of `eden db migrate`

- **Line 170**: Raw SQL
  - Missing: Show if/how to execute raw SQL

- **Line 193**: Model indexing patterns
  - Missing: Show `index=True` parameter

### docs/tutorial/task4_routing.md

- **Line 13**: `from eden import Router` - shown ✅
  - Missing: `from app.models import User`

- **Line 32**: `Response`, `status` usage
  - Missing: `from eden import Response, status` or `from starlette`

- **Line 50**: `Request` class usage
  - Missing: `from eden import Request`

- **Line 78**: Form data parsing with `request.form()`
  - Missing: Context about async

- **Line 105**: Schema validation imports
  - Missing: `from pydantic import BaseModel, EmailStr`

- **Line 149**: Module organization with imports
  - Missing: `from eden import Router`

- **Line 185**: Template rendering
  - Missing: `from eden import render_template`

### docs/tutorial/task5_templating.md

- **Line 86**: Template directives like `@yield`, `@extends`
  - Missing: Explanation of which template engine provides these

- **Line 98**: `@span()` directive
  - Missing: Explanation of Eden's templating dialect

### docs/tutorial/task6_forms.md

- **Line 15**: `from eden.forms import Schema, field, EmailStr` - shown ✅
  - Missing: Code blocks later use `class UserCreateSchema(Schema)` without showing the Schema definition in scope

- **Line 51**: `@user_router.validate()` decorator
  - Missing: Shown but not in imports section of code block

- **Line 157**: `@field_validator` without import shown in context
  - Missing: `from pydantic import field_validator`

- **Line 188**: Dynamic form conditions
  - Missing: How to handle dynamic field visibility

- **Line 234**: Ajax form submission
  - Missing: JavaScript context

- **Line 275**: Multi-step form handling
  - Missing: State management context

### docs/tutorial/task7_security.md

- **Line 13**: `from eden.auth import roles_required, login_required`
  - Missing: But then uses `@roles_required` in later code blocks without re-importing

- **Line 50**: `@admin_router.get()` without router import
  - Missing: `router = Router()` definition not shown

- **Line 72**: `Forbidden` exception
  - Missing: `from eden.exceptions import Forbidden`

- **Line 95**: Custom permission class
  - Missing: Inheritance or base class not shown

- **Line 126**: `@post_router.put()` without router definition
  - Missing: Router initialization

- **Line 149**: Session configuration
  - Missing: Import paths for Session class

- **Line 169**: Hash and verify functions
  - Missing: `from eden.auth import hash_password, verify_password`

- **Line 248**: Two-factor setup
  - Missing: All imports for TOTP functions

### docs/tutorial/task8_saas.md

- **Line 13**: Admin registration code
  - Missing: `from eden.admin import admin`

- **Line 41**: `stripe_client` without imports
  - Missing: `from eden.payments import stripe_client`

- **Line 55**: `storage` API without imports
  - Missing: `from eden import storage, S3StorageBackend`

- **Line 73**: `stripe_webhook` decorator
  - Missing: `from eden.payments import stripe_webhook`

- **Line 107**: `Subscription` model
  - Missing: Model definition not shown

- **Line 135**: Multi-tenancy with `Tenant` model
  - Missing: Full model definition with imports

- **Line 157**: Analytics tracking
  - Missing: `from eden.telemetry import record_metric`

- **Line 195**: StripeProvider setup
  - Missing: `from eden.payments import StripeProvider`

### docs/tutorial/task9_deployment.md

- **Line 104**: Docker userland setup
  - Missing: Context about `adduser` command availability

- **Line 220**: Environment file usage
  - Missing: How env variables are loaded (python-dotenv?)

### docs/tutorial/task10_testing.md

- **Line 13**: `import pytest` and `from app.models import User`
  - Missing: But pytest asyncio plugin not shown

- **Line 39**: `AsyncClient` setup
  - Missing: `from httpx import ASGITransport, AsyncClient`

- **Line 96**: Schema validation testing
  - Missing: Schema import context

- **Line 136**: Security testing with tokens
  - Missing: How user tokens are generated

- **Line 187**: Transaction testing
  - Missing: Database transaction context manager import

- **Line 241**: Edge case testing
  - Missing: Exception classes import

---

## Getting Started Issues

### docs/getting-started/example-snippets.md

- **Line 7-25**: "Hello World" example shows all imports ✅
  
- **Line 26-58**: "Models and ORM" example
  - Missing: `from eden import Model, StringField, IntField, BoolField` - wait, these are shown, but then later examples use them without repeating import

- **Line 59-99**: "REST API Endpoints" 
  - Missing: `from eden import Request` - not shown in code block

- **Line 100-133**: "Routing and Path Parameters"
  - Missing: Imports for Request

- **Line 134-172**: "Authentication & Sessions"
  - Missing: `from eden import login_required`

- **Line 173-207**: "Templates & HTML Rendering"
  - Missing: `from eden import render_template`

- **Line 208-231**: "Relationships"
  - Missing: `from eden import ForeignKeyField`

- **Line 232-262**: "Filtering and Queries"
  - Missing: `from eden import Q, F`

- **Line 263-287**: "Middleware"
  - Missing: Middleware not fully detailed

- **Line 288-312**: "Error Handling"
  - Missing: `from eden import Exception, NotFound, Unauthorized, Forbidden`

- **Line 313-347**: "Background Tasks"
  - Missing: `from eden.tasks import background_task` - not shown

- **Line 348-375**: "Pagination"
  - Missing: Context about models

- **Line 376-428**: "Async Operations"
  - Missing: Various imports

- **Line 429-461**: "Caching"
  - Missing: `from eden.cache import cache`

- **Line 462-509**: "Custom Validators"
  - Missing: Pydantic imports

- **Line 510-539**: "Signal/Event System"
  - Missing: Where signal system comes from

- **Line 540-571**: "Database Migrations"
  - Missing: Alembic/Eden migration system imports

- **Line 572-603**: "Environment Variables"
  - Missing: `import os` shown implicitly

- **Line 604-637**: "Logging"
  - Missing: `from eden import setup_logging`

- **Line 638-695**: "Testing"
  - Missing: Multiple pytest and testing imports

- **Line 696-718**: "Performance Tuning"
  - Missing: Monitoring and profiling imports

- **Line 719**: Final section incomplete

### docs/getting-started/installation.md

- **Line 130**: Simple app example
  - Missing: What happens if imports fail

- **Line 254**: Virtual environment activation
  - Missing: Context about shell availability

- **Line 341**: Version checking
  - Missing: sqlalchemy import context

- **Line 368**: CLI help context
  - Missing: eden CLI availability

### docs/getting-started/learning-path.md

- Various code snippets reference other guides
  - Missing: Links are present but actual imports in examples vary

---

## Severity Classification

### `CRITICAL` - Blocks Example Execution (19 files)
- philosophy.md (lines: 89, 147, 162, 184, 199)
- quickstart.md (lines: 49, 285, 360)
- auth.md (lines: 13, 18, 38, 65, 85, 129)
- advanced-routing.md (lines: 13, 44, 64, 90, 104)
- structure.md (lines: 87, 106, 179)

### `HIGH` - Examples Partially Broken (24+ files)
- csrf-protection.md (8+ lines)
- caching.md (6+ lines)
- formfield-api.md (7+ lines)
- components.md (4 lines)
- All tutorial files (task2-10)

### `MEDIUM` - Unclear Dependencies (10+ files)
- admin.md
- api.md
- background-tasks.md
- dependencies.md
- core-app.md
- installation.md

### `LOW` - Missing Clarification
- example-snippets.md (inline) 
- learning-path.md

---

## Recommendations

1. **Add Import Headers**: Every code block should show all necessary imports
2. **Use Import Groups**: Group imports by source (eden, pydantic, external)
3. **Add "Next Steps" Hints**: When code references undefined entities, add a "Note" box explaining where they come from
4. **Create Import Reference Table**: Add a table at the start of each guide showing all imports needed
5. **Validation Script**: Create a Python script to extract and validate all code blocks
6. **Code Block Language Tags**: Ensure all Python blocks are marked with ```python for syntax highlighting
