# CLI Suite: Elite Forge & Scaffolding 🛠️

Eden provides a high-performance command-line interface designed to accelerate your development workflow from initial scaffolding to production deployment.

---

## 🌿 Project Scaffolding: `eden new`

Start every project with the interactive project wizard.

```bash
eden new my-awesome-project
```

The wizard will guide you through:

1. **Scale**: Choose between **Minimal (one file)** for small services or **Complete (modular)** for enterprise applications.
2. **Database**: Automatic configuration for **SQLite** or **Postgres**.
3. **Extras**: Instant integration for **Admin UI**, **Stripe Payments**, **WebSockets**, and **Email**.

---

## 🔨 Elite Forge: `eden generate`

Eden Forge is the framework's code generation engine. It doesn't just create files; it understands your project layout and **auto-registers** code into your application.

### `eden generate model`

Scaffolds a new database model with rich metadata support.

```bash
eden generate model Task
```

### `eden generate route`

Creates a modular router and connects it to your main application.

```bash
eden generate route billing
```

---

## 🗄️ Database Management: `eden db`

Manage your schema evolution with integrated migrations.

| Command | Description |
| :--- | :--- |
| `eden db init` | Initialize the migration environment. |
| `eden db generate -m "..."` | Create a new migration script from model changes. |
| `eden db migrate` | Apply all pending migrations. |
| `eden db rollback` | Revert the last applied migration. |
| `eden db check` | Scan for schema drift. |

---

## 🛡️ Authentication: `eden auth`

Manage users and security from the terminal.

### `eden auth createsuperuser`

Create an administrative account with full permissions.

```bash
eden auth createsuperuser --email "admin@example.com" --full-name "Admin"
```

---

## 🚀 Execution & Management

### `eden run`

Launch your development server with auto-reload.

```bash
eden run --port 8080
```

### `eden tasks`

Manage and monitor background task queues.

```bash
eden tasks worker
```

---

> [!TIP]
> Use `eden --help` to see a full list of commands and options. Most groups support `--help` for subcommand details, such as `eden db --help`.

**Next Steps**: [Deployment Guide](deployment.md)
