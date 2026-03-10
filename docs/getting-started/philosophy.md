# The Eden Ethos 🌿

Eden is not just another web framework; it is a philosophy of **"Elite-First"** development. It was born from the realization that modern developers are often forced to choose between speed (DX), performance (execution), and security. 

In Eden, we believe you should never have to compromise.

## Core Values

### 1. Aesthetics by Default
We believe that professional software should look professional. From our built-in design tokens to the glassmorphic debug interface, Eden ensures that even your error pages provide a premium experience.

### 2. Conventional Excellence
Borrowing from the "Convention over Configuration" mantra of Django, but maintaining the lightweight flexibility of FastAPI and Flask, Eden provides sane defaults that "just work" while allowing you to peel back the layers when needed.

### 3. Security as a Core Primitive
Security is not a plugin in Eden; it's a first-class citizen. CSRF protection, secure headers, and row-level multi-tenancy are baked into the core engine, ensuring your applications are safe by default.

### 4. Developer Joy
We prioritize the developer's experience (DX). This means clear error messages, intuitive APIs, and a command-line interface that allows you to forge new features at the speed of thought.

## Opinionated Architecture

Eden is opinionated where it matters most: **Project Structure**, **Data Integrity**, and **Aesthetic Standards**. By removing the burden of these foundational decisions, we allow you to focus on your unique business logic.

---

## The Three Pillars of Eden

### I. Elite Performance (Async-Native)
Every component in Eden is built for the modern, asynchronous web. From our database drivers to our template rendering engine, everything is non-blocking. This ensures that your application can handle thousands of concurrent users with minimal resource overhead.

```python
# Synchronous (Standard) - Blocking IO
def get_data():
    return db.query(...) 

# Eden (Elite) - Non-blocking IO
async def get_data():
    return await User.filter(...)
```

### II. DX-First (The Forge)
We believe that a framework should be your partner, not your master. Our CLI, **The Forge**, acts as an automated architect, scaffolding resources, models, and migrations so you can prototype in minutes, not days.

### III. Security at the Core (The Vault)
In many frameworks, security is an afterthought. In Eden, it is the first thing we check.
- **CSRF**: Initialized by default on all state-changing routes.
- **Multi-Tenancy**: Built-in row-level isolation that prevents data leakage between organizations.
- **Argon2**: The industry standard for password hashing, used as our default.

---

## When to Use Eden?

Eden is ideal for:
- **SaaS Platforms**: Where multi-tenancy and security are paramount.
- **Enterprise Internal Tools**: Where professional aesthetics and rapid development are required.
- **Modern Web APIs**: Where execution speed and type safety cannot be ignored.

---

**Next Steps**: [Installation Guide](installation.md)
