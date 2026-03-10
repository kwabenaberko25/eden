# CLI Suite 🛠️

The Eden CLI is your essential companion for project management, code generation, and database administration. It is designed to be fast, discoverable, and powerful.

## Core Commands

These commands handle the basic lifecycle of your Eden projects.

### `eden version`
Displays the current version of the Eden Framework.

### `eden run`
Starts the development server. By default, it looks for an `app.py` file and enables hot-reloading.

```bash
# Start on default port (8000)
eden run

# Start on a custom port
eden run --port 9000
```

---

## The Forge ⚒️

"The Forge" is Eden's code generation and project scaffolding tool.

### `eden new`
Creates a new project from a standard template.

```bash
npx eden new my_app
```

### `eden db history`
Lists all migrations applied to the current database.

### `eden db generate`
Generates a raw SQL script for the current state of the database. Useful for deployments without Alembic.

### `eden db check`
Verifies if the database schema is in sync with your models without applying any changes.

---

## The Forge ⚒️ (Scaffolding Reference)

The Forge is your rapid-prototyping engine. It identifies your dependencies and generates best-practice code.

| Command | Usage | Output |
| :--- | :--- | :--- |
| `generate model` | `eden forge generate model Profile` | A new `EdenModel` file in `models/`. |
| `generate resource` | `eden forge generate resource Post` | A full `Resource` class with CRUD logic. |
| `generate route` | `eden forge generate route Search` | A new `Router` with boilerplate handlers. |
| `generate schema` | `eden forge generate schema User` | A Pydantic schema for API validation. |

---

## User Management (`eden auth`) 🔑

Manage your application's users directly from the terminal.

### `eden auth create-user`
Creates a new user account.

```bash
eden auth create-user --email admin@eden.dev --admin
```

### `eden auth list-users`
Lists all registered users.

---

## Background Tasks (`eden tasks`) ⚙️

Monitor and manage your background workers.

### `eden tasks run`
Starts the task worker (EdenBroker).

### `eden tasks status`
Checks the health and status of the task queue.

---

**Next Steps**: [Database & ORM](orm.md)
