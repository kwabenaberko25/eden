# Database Migrations 🏗️

Eden uses **Alembic** under the hood to provide a robust, version-controlled migration system that evolves your schema as your models change.

## The Workflow

The standard cycle for database changes in Eden consists of three mandatory steps:

1.  **Initialize**: Set up the migration environment (first time only).
2.  **Generate**: Detect model changes and create a migration file.
3.  **Apply**: Execute the migration to update the physical database.

> [!IMPORTANT]
> You **must** generate and apply a migration before you can perform administrative tasks (like creating a superuser). Creating the migration environment with `init` does not create the database tables.

---

## CLI Reference

| Command | Description |
| :--- | :--- |
| `eden db init` | Create the `migrations/` directory and `alembic.ini`. |
| `eden db generate -m "description"` | Auto-detect model changes and create a revision script. |
| `eden db migrate` | Apply all pending migrations (shorthand for `upgrade head`). |
| `eden db upgrade head` | Apply all pending migrations to the database. |
| `eden db upgrade +1` | Apply only the next migration. |
| `eden db downgrade -1` | Revert the last applied migration. |
| `eden db history` | List all available and applied migrations. |
| `eden db check` | Scan for schema drift across all tenants. |

---

## Detailed Example: Initial Setup

When starting a new Eden project, follow this exact sequence to prepare your database:

### 1. Initialize
```bash
eden db init
```
This creates your `migrations/` structure. By default, Eden auto-imports core models (Auth, Tenancy) in `migrations/env.py`.

### 2. Generate Initial Migration
```bash
eden db generate -m "initial setup"
```
Eden will scan `eden.auth.models` and your local models to create `/migrations/versions/xxxx_initial_setup.py`.

### 3. Apply the Migration
```bash
eden db migrate
```
Your database tables (including `eden_users`) are now physically created.

### 4. Create Superuser (Next Step)
Now that the tables exist, you can safely create your administrator:
```bash
eden auth createsuperuser
```

---

## Detailed Example: Adding a New Field

### 1. Update your Model
```python
class User(Model):
    name: str = f()
    phone_number: str = f(nullable=True) # New field
```

### 2. Generate Migration
```bash
eden db generate -m "Add phone to user"
```

### 3. Apply
```bash
eden db migrate
```

---

## Best Practices

- **Never Delete Migrations**: If you made a mistake, create a new "fix" migration rather than editing an old one.
- **Check-in Scripts**: Always commit the `migrations/` directory to your version control system.
- **Schema Drift**: Periodically run `eden db check` to ensure your physical database matches your model definitions.
- **Constraints**: Be careful when adding `NOT NULL` constraints to existing tables with data; either provide a default or do it in two steps.

---

**Next Steps**: [Authentication Overview](auth.md)
