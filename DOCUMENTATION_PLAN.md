# Eden Framework Documentation Plan

## Modular Architecture & Logical Progression

The documentation follows a "Pedagogical Flow," guiding the user from foundational concepts to advanced production patterns.

### Section I: Philosophical Foundations
1. **The Eden Ethos**: Philosophy behind the framework, speed/DX/security balance.
2. **Scaffold & Architecture**: In-depth look at project structure and core lifecycle.

### Section II: The Command Line Interface (CLI)
3. **Eden CLI Reference**: Comprehensive guide to `eden run`, `eden new`, and `eden version`.
4. **The Data Forge (`eden forge`)**: Mastery of code generation and migration lifecycle.

### Section III: The Data Layer (ORM)
5. **The Data Forge (Models)**: Defining entities using `Model`, `Mapped`, and field helpers.
6. **The QuerySet API**: Chainable queries, `Q` and `F` expressions, aggregates, and pagination.

### Section IV: The Unified Layer (Resources)
7. **Unified Resources**: Combining Models, Forms, and Routers into a single domain entity.
8. **Action Decorators**: Adding custom behaviors to resources.

### Section V: Premium UI & Interactivity
9. **Eden Templates**: Directive-based syntax (`@if`, `@for`, `@section`, etc.), inheritance, and filters.
10. **The Reactive Pulse (HTMX)**: Single-template fragment rendering and zero-JS interactivity.

### Section VI: Input & Validation
11. **Eden Forms**: Pydantic-powered forms, rendering, and widget manipulation.

### Section VII: The Fortress (Security)
12. **Multi-Tenancy**: Request-scoped isolation strategies (subdomain, header, path).
13. **Role-Based Access Control (RBAC)**: Row-level security policies (`AllowOwner`, `AllowRoles`).

### Section VIII: Ecosystem & Production
14. **Integrations**: Storage (S3), Mail, Payments, Background Tasks.
15. **Observability**: Performance Telemetry and Logging.
16. **Deployment**: Docker-first strategies and production tuning.

---

## Documentation Quality Standards

### Voice & Tone
- **Professional & "Elite"**: Use high-standard technical language but maintain accessibility.
- **Pedagogical**: Always explain the *why* before the *how*.
- **Direct**: Avoid fluff; focus on working code and practical patterns.

### Syntax Standards (The "Eden Way")
- **Never** use raw Jinja2 syntax (`{% %}`). Always use Eden directives (`@`).
- **Never** use raw SQLAlchemy `Column`. Always use `Mapped` and `StringField`/`IntField` etc.
- **Prefer** `Resource` over manual `Model` + `Router` for CRUD features.
- **Prefer** `from eden.db import Mapped` over `from sqlalchemy.orm import Mapped`.

### Interactive Learning
Each phase includes:
- **Executable Snippets**: Modular code that can be copied into a project.
- **Verification Steps**: Concrete ways to test if the concept is understood.
- **Edge Cases**: Documentation of common pitfalls and performance considerations.
