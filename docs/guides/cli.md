# CLI Suite: Mastering the `eden` Command 💻

Eden's command-line interface is designed to automate repetitive tasks and manage your application's lifecycle from development to production.

## Core Commands

### `eden start`
Starts the development server.
- **Auto-reload**: Restarts whenever code changes.
- **Debug Port**: Default is `8000`.
- **Options**:
  - `--host`: Host to bind to (default: `127.0.0.1`).
  - `--port`: Port to listen on (default: `5000`).

### `eden init [name]`
Scaffolds a new Eden project with the "Premium" structure.
- Creates folders: `app/`, `eden/`, `static/`, `templates/`.
- Generates: `app.py`, `models.py`, `eden.json`, `.env`.

---

## Database Migrations (`eden migrate`)

Manage your schema evolution.

- **`create [message]`**: Generates a new migration script based on model changes.
- **`upgrade head`**: Applies all pending migrations.
- **`downgrade -1`**: Reverts the last migration.
- **`history`**: View the list of migrations.

---

## Static Assets (`eden assets`)

Optimize your frontend for production.

- **`build`**: Minifies and hashes assets in your `static/` folder.
- **`clean`**: Removes old hashed assets.

---

## Task Management (`eden tasks`)

Manage your background workers (requires `[tasks]` extra).

- **`worker`**: Starts the taskiq-based background worker.
- **`scheduler`**: Starts the periodic task scheduler (cron jobs).

---

## User & Auth Management

### `eden createsuperuser`
Creates an administrative user with full permissions. It will prompt for email and password.

### `eden changepassword [email]`
Resets the password for a specific user.

---

## Custom CLI Commands

You can extend the Eden CLI with your own commands by using the `@app.command` decorator.

```python
# app.py
@app.command(name="sync-stripe", help="Sync customers from Stripe")
async def sync_stripe():
    # your logic here
    print("Done! 🎉")
```

Now you can run it via:
```bash
eden sync-stripe
```

---

**Next Steps**: [Deployment Guide](deployment.md)
