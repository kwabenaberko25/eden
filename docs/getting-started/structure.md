# Project Structure 🏗️

A standard Eden project follows a clean, modular layout designed for both small sites and enterprise-grade SaaS applications.

## The Default Layout

When you run `eden new`, your project will follow a **Premium-Flat** layout:

```text
my_project/
├── app.py          # App initialization & middleware (Premium)
├── models.py       # Domain models
├── settings.py     # Application settings
├── routes/         # Routes package
│   └── __init__.py # Main router
├── static/         # CSS, JS, Images
├── templates/      # HTML templates (@directives)
├── tests/          # Pytest suite
│   └── conftest.py # Test configuration
├── .env.example    # Environment template
├── Dockerfile      # Container config
└── docker-compose.yml
```

## Core Configuration

### `.env`
Your project secrets and environment-specific toggles live here. Eden automatically loads these into `app.config`.

```text
DEBUG=True
SECRET_KEY=y0ur-5ecr3t-k3y
DATABASE_URL=sqlite+aiosqlite:///db.sqlite3
```

### `eden.json`
This file contains framework-level metadata used by **The Forge** and the CLI to manage your project's identity and dependencies.

## Core Files Explained

### `app.py`
The "heart" of your application. This is where you instantiate `Eden`, configure the middleware stack (Security, Session, CSRF, etc.), and mount your routers.

### `models.py`
Domain models inheriting from `Model` live here. By default, Eden provides a flat `models.py` for simplicity, but you can convert this to a package as your domain grows.

### `settings.py`
Global application settings and environment-variable lookups. This file keeps your `app.py` clean by separating configuration from initialization logic.

### `/routes`
We recommend grouping related routes into this package. Use the `Router` class to create modular endpoints that are then mounted in `app.py`.

### `/static`
Files placed here are served automatically. In production, we recommend serving these via a CDN or a web server like Nginx, but Eden handles them natively for development.

## Scalability Tip
As your project grows, encapsulate your domain logic into **Resources**. A Resource in Eden combines a Model, a Router, and Forms into a single unit of functionality.

---

**Next Steps**: [Routing Guide](../guides/routing.md)
