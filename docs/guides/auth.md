# Authentication & Security 🛡️

Eden provides a modular, industrial-grade security suite designed to handle everything from simple blogs to complex multi-tenant SaaS platforms.

## Core Philosophy

Security in
The Eden ORM is built on three core principles:

- **Async-First**: All database operations are non-blocking.
- **Type-Safety**: Deep integration with Python type hints.
- **Developer Experience**: Intuitive, Django-inspired API.
ersisted Logs).

---

## The `User` Model

All authentication revolves around the `User` model. Eden provides a `BaseUser` that includes standard security fields, which you can extend.

```python
from eden.auth import User

# Check status easily
if request.user.is_authenticated:
    print(f"Hello, {request.user.name}")
```

---

## Security Middleware Suite 🧱

Eden protects your app automatically when you enable the security suite.

```python
app.add_middleware("security")  # CSP, HSTS, X-Frame-Options
app.add_middleware("csrf")      # Cross-Site Request Forgery
app.add_middleware("ratelimit") # Bruteforce protection
```

---

## Technical Guides

Explore specialized guides for each part of the security system:

### 1. [Session Management](sessions.md)
Learn about secure cookies, session lifecycles, and how Eden remembers users.

### 2. [Role-Based Access (RBAC)](auth-rbac.md)
Define roles like `admin` and `editor` and protect routes using decorators like `@roles_required`.

### 3. [Social Login (OAuth)](auth-oauth.md)
Integrate Google, GitHub, and other providers with zero-friction onboarding.

### 4. [Multi-Tenancy Patterns](tenancy.md)
Learn how `TenantMixin` ensures data isolation in shared database environments.

---

## Security Checklist

Before going to production, ensure:
- [ ] `DEBUG` is set to `False`.
- [ ] `SECRET_KEY` is a long, random string.
- [ ] All forms use the `@csrf` directive.
- [ ] `SESSION_COOKIE_SECURE` is `True` (requires HTTPS).
- [ ] Rate limits are applied to sensitive routes (Login, Signup).

---

**Next Steps**: [Templating System](templating.md)
