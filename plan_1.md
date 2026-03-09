# Eden Framework Tutorial Development Plan

## Overview

Create a comprehensive, structured tutorial and reference guide covering every feature in progressive complexity, from absolute beginner to production-ready implementations, using only native Eden abstractions.

---

## Tutorial Structure (10 Phases)

### Phase 1: First Application (Beginner)
**File**: `tutorial/01_first_application.md`

Content:
- Installing Eden (`uv pip install eden-framework`)
- Creating first app (`eden new project_name`)
- Application structure (Nexus heart)
- Running development server (`eden run`)
- Route decorators (`@app.get`, `@app.post`, etc.)
- Return value handling (automatic JSON/HTML conversion)
- Path parameters with type conversion
- Modular routers (`Router`)
- Complete example: Task Manager API

---

### Phase 2: The Data Forge (Beginner-Intermediate)
**File**: `tutorial/02_data_modeling.md`

Content:
- Database setup (`Database`)
- Creating models with `Model` and `Mapped` from `eden.db`
- Field helpers: `StringField`, `IntField`, `BoolField`, `DateTimeField`, `UUIDField`, `TextField`, `FloatField`
- Primary keys and UUID defaults
- CRUD operations: `create`, `read`, `update`, `delete`
- Automatic migrations with `eden forge migrate`
- Complete example: Blog models

---

### Phase 3: The QuerySet API (Intermediate)
**File**: `tutorial/03_queryset_api.md`

Content:
- Fluent lazy-loading interface
- Filter methods: `filter`, `exclude`, `order_by`, `limit`, `offset`
- Eager loading with `prefetch()`
- Complex lookups with `Q` objects
- Atomic updates with `F` expressions
- Aggregations: `Count`, `Sum`, `Avg`, `Min`, `Max`
- Pagination with `Page` object
- Soft delete with `SoftDeleteMixin`

---

### Phase 4: Premium UI & Templating (Intermediate)
**File**: `tutorial/04_templating.md`

Content:
- Eden directive syntax (`@extends`, `@block`, `@if`, `@for`)
- Template inheritance and `@section` / `@push`
- Built-in filters (`time_ago`, `money`, `slugify`)
- Asset management (`@eden_head`, `@eden_scripts`)
- Component system (`@component("name") { ... }`)
- Class name helpers (`class_names`)

---

### Phase 5: Reactive Interactivity (Intermediate)
**File**: `tutorial/05_htmx_integration.md`

Content:
- HTMX Zero-JS philosophy
- Fragment rendering with `@fragment("name") { ... }`
- Request guards: `@htmx` and `@non_htmx`
- Automatic fragment detection in `TemplateResponse`
- Interactive examples: Inline editing, live search

---

### Phase 6: Input Governance (Intermediate-Advanced)
**File**: `tutorial/06_forms_validation.md`

Content:
- `BaseForm` class wrapping Pydantic schemas
- Synchronous validation with `form.is_valid()`
- Form rendering: `@for(field in form)` and `@render_field(field)`
- Widget tweaks: `field.add_class()`, `field.attr()`
- Handling file uploads in forms
- CSRF protection (`@csrf`)

---

### Phase 7: The Unified Layer (Advanced)
**File**: `tutorial/07_resources.md`

Content:
- `Resource` class architecture
- Automated CRUD routing with `Resource.router()`
- Resource-linked forms (`Resource.get_form()`)
- Custom resource actions with `@action`
- Content negotiation (HTML vs JSON)

---

### Phase 8: The Fortress - Security (Advanced)
**File**: `tutorial/08_security.md`

Content:
- Session-based authentication
- Password hashing and User models
- Row-Level RBAC policies (`AllowOwner`, `AllowRoles`)
- Request-scoped Multi-Tenancy (`TenantMixin`, `TenantMiddleware`)
- Security strategies: Subdomain vs Header isolation

---

### Phase 9: Ecosystem Integrations (Expert)
**File**: `tutorial/09_ecosystem.md`

Content:
- Background tasks with `taskiq`
- Email sending with `configure_mail`
- File storage with `S3StorageBackend`
- Payment processing with `Subscription` and `WebhookRouter`

---

### Phase 10: Performance & Production (Expert)
**File**: `tutorial/10_production.md`

Content:
- Performance Telemetry and `Server-Timing` headers
- Middleware stack optimization
- Caching strategies
- Docker-first deployment
- Logging and professional observability

---

## Quality Standards

Each phase must include:
- **Eden-Native Only**: Directives over Jinja tags, Field helpers over raw columns.
- **Pedagogical Progression**: Build a single cohesive project through all phases.
- **Verification**: Concrete test steps for every new concept.
- **Elite DX**: Examples must be beautiful and copy-paste ready.

