# 🛠️ CLI Suite: High-Speed Scaffolding

**Accelerate your development cycle with the Eden CLI—a professional command-line suite designed for rapid prototyping and enterprise-grade code generation. From initial project architecture to complex multi-tenant migrations, Eden provides an "Elite Forge" to handle the boilerplate for you.**

---

## 🧠 Conceptual Overview

The Eden CLI is more than just a task runner; it's a **Project Lifecycle Manager**. It interacts directly with the Eden application context to understand your models, routes, and configuration, ensuring that all generated code is automatically registered and follows the framework's strict architectural patterns.

### The CLI Architecture

```mermaid
graph TD
    A["Developer"] --> B["Eden CLI: Entry Point"]
    B --> C["Forge Engine: Code Generation"]
    B --> D["DB Manager: Migration Suite"]
    B --> E["Identity: Auth & Superuser"]
    C --> F["Auto-Registration: "main.py Injection"]
    D --> G["Multi-Schema Strategy: Postgres/SQLite"]
    F --> H["Project: models / routes / templates"]
```

---

## 🌿 Project Initiation: `eden new`

Start every high-fidelity project with the interactive project wizard.

```bash
eden new my-enterprise-app
```

The wizard allows you to select your **Scale** and **Features** upfront:
-   **Scale**: `Minimal` (Single-file) for microservices or `Complete` (Modular) for SaaS.
-   **Database**: Automatic setup for `SQLite` (Local) or `Postgres` (Production).
-   **Elite Features**: Pre-configure **Stripe**, **Redis Caching**, and **Social Auth** with zero manual wiring.

---

## 🔨 The Elite Forge: `eden generate`

The "Forge" is the crown jewel of the Eden CLI. It doesn't just create files; it understands your project structure and **auto-registers** your new code into the main application.

### 1. Generating Models
Scaffold a new ORM model with full Pydantic validation and Admin UI support.

```bash
eden generate model Task --tenant-aware --audit
```
*Creates `models/task.py` and registers it with the database registry.*

### 2. Generating Routes & Routers
Create a modular router and automatically mount it to your main `Eden` instance.

```bash
eden generate router billing --path /api/v1/billing
```
*Creates `routes/billing.py` and injects the `app.include_router()` call into your main application.*

### 3. Class-Based Views
Scaffold complex logic with standard Eden patterns for CRUD or Custom Actions.

```bash
eden generate view ProfileView --template profile.html
```

---

## 🗄️ Database & Environment: `eden db` & `eden sync`

Manage your schema evolution with integrated migrations that support multi-schema SaaS strategies out of the box.

| Command | Elite Capability |
| :--- | :--- |
| `eden db init` | Initializes the `alembic` environment for async migrations. |
| `eden db generate -m "..."` | Auto-detects model changes and generates a revision script. |
| `eden db migrate` | Applies pending migrations (Handles multiple schemas for Postgres). |
| `eden db check` | Verifies the physical database matches your ORM definitions. |
| `eden sync` | **Atomic Sync**: Runs `check` and `migrate` in one command. |

> [!TIP]
> Use `eden sync --all-tenants` for local development when you have multiple specialized schemas that need to stay in lock-step with your core model definitions.

---

## 🛡️ Identity Management: `eden auth`

Manage users and security from the terminal.

### `eden auth createsuperuser`
Create an administrative account with full shell permissions.

```bash
eden auth createsuperuser --email "ops@eden.sh" --full-name "DevOps Admin"
```

---

## 🏢 SaaS Operations (Tenant Management)

Provision and manage tenants directly from the terminal without manual SQL.

```bash
# Provision a new tenant for a client
eden tenant provision --name "Initech Corp" --plan "enterprise"

# Shortcut to reconcile all tenant schemas
eden sync --all-tenants
```

---

## 🏎️ Developer Power Tools: `shell` & `test`

Eden provides high-utility commands to reduce context switching during core feature development.

### 1. The Interactive Shell: `eden shell`
Launch a pre-configured IPython shell with your entire application context loaded. No more dry imports.

```python
# $ eden shell
>>> app.db
<eden.db.Database object at 0x...>
>>> await User.query(session).all()
[...]
```

### 2. The Integrated Test Runner: `eden test`
A wrapper around `pytest` that enforces Eden's testing standards, including automatic database cleanup and environment isolation.

```bash
# Run all tests
eden test

# Run specific module with fail-fast
eden test tests/test_auth_rbac.py --fail-fast
```

---

## 🚀 Execution & Monitoring

### `eden run`
Launch your development server with high-fidelity logging and auto-reload.

```bash
eden run --port 8000 --workers 4
```

### `eden tasks`
Manage and monitor background task queues and periodic schedulers.

```bash
# Start a task worker
eden tasks worker

# Start the periodic task scheduler (Cron)
eden tasks scheduler
```

---

## 💡 Best Practices

1.  **Forge First**: Never create a model or route from scratch. Use the `forge` to ensure all boilerplate (imports, registrations) is handled correctly.
2.  **Migration Safety**: Always run `eden db check` before committing code to ensure your local schema is in sync with your models.
3.  **Tenant Provisioning**: Use the `eden tenant` commands for local testing of multi-tenant isolation before deploying to production.
4.  **Audit Your Schema**: Regularly use `eden db check --drift` in CI/CD to prevent manual DB changes from breaking the ORM.

---

**Next Steps**: [Deployment & Scaling](deployment.md)
