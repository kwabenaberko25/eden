# CLI Suite 🛠️

The Eden CLI is your essential companion for project management, code generation, and database administration.

## Core Commands

### `eden version`
Displays the current version of the Eden Framework.

### `eden run`
Starts the development server with auto-discovery and hot-reloading.

```bash
# Start auto-detecting app.py/main.py
eden run

# Specify app instance manually
eden run --app main:app --port 8000
```

### `eden new`
Scaffolds a premium, production-ready Eden project with Docker and Pytest.

```bash
# Basic setup (creates a folder)
eden new my_awesome_app

# Current directory setup
eden new my_awesome_app .

# Specify database choice (sqlite, postgresql, mysql)
eden new my_awesome_app --db postgresql
```

---

## The Forge ⚒️

"The Forge" is Eden's rapid scaffolding engine. In the new **Premium-Flat** structure, it generates code relative to your project root.

| Command | Usage | Output |
| :--- | :--- | :--- |
| `model` | `eden forge model Post` | Appends to or creates `models.py`. |
| `route` | `eden forge route Blog` | Creates a router in `routes/`. |
| `component` | `eden forge component Navbar` | Creates a UI component. |
| `entity` | `eden forge entity Product` | Full stack: Model + Schema + CRUD Router. |
| `resource` | `eden forge resource Post` | Unified Resource: Model + Router + Templates. |

---

## Database Management (`eden db`) 🗄️

Manage migrations and schema drift across all tenants.

### `eden db init`
Initializes the `migrations/` directory and `alembic.ini`.

### `eden db generate`
Generates a new versioned migration script based on model changes.

```bash
eden db generate -m "add_user_profile"
```

### `eden db migrate`
Applies all pending migrations to the database.

### `eden db check`
🕵️ Detects schema drift between your models and the actual database state across all tenants.

---

## Authentication (`eden auth`) 🔑

### `eden auth createsuperuser`
Creates an administrative user with full permissions.

```bash
eden auth createsuperuser
```

---

## Background Workers ⚙️

Eden uses a distributed task queue for background processing.

### `eden worker`

Starts one or more worker processes to consume tasks.

```bash
eden worker --workers 4
```

### `eden scheduler`

Starts the periodic task scheduler for cron-style jobs.

```bash
eden scheduler
```

---

**Next Steps**: [Database & ORM](orm.md)
