# Enhanced Prompt: Deep Integrated Eden Tutorial

## Objective
Design and implement a comprehensive, deep-integrated tutorial for the Eden Framework documentation. This tutorial will guide users from initial project setup (directory creation, dependency installation) through to production deployment, showcasing every major feature of the Eden ecosystem.

## Source Code Context & Requirements
Based on analysis of the Eden source code (`C:\ideas\eden`), the tutorial must adhere to the "Eden Way" and reference actual implementation details:

1. **CLI Integration**:
   - Utilize `eden new <project_name>` for scaffolding (see `eden/cli/main.py:98-375`).
   - Demonstrate `eden run` for development server (see `eden/cli/main.py:27-96`).
   - Cover `eden generate/forge` for code generation.

2. **Core Application Structure**:
   - Follow the scaffolding output structure (app/, static/, templates/, models/, routes/).
   - Initialize `Eden` app instance (see `eden/app.py:39-120`).
   - Configure database via `Database("sqlite+aiosqlite:///db.sqlite3")` (see `eden/app.py:100-113`).

3. **Data Layer (ORM)**:
   - Define models using `EdenModel`, `Mapped`, and field helpers (`StringField`, `IntField`, `ForeignKeyField`) (see `eden/__init__.py:15-36`).
   - Demonstrate `auto-session injection` for queries (see `tutorial.md:45-46`).
   - Use `Resource` for CRUD operations (see `eden/resources.py`).

4. **UI & Templating**:
   - Use Eden's directive-based syntax (`@if`, `@for`, `@component`) instead of raw Jinja2 (see `README.md:62-98`).
   - Setup `EdenTemplates` (see `eden/app.py:228-241`).

5. **Security & Middleware**:
   - Add built-in middleware: `security`, `csrf`, `ratelimit` (see `eden/app.py:319-332`).
   - Implement RBAC with `@roles_required` (see `eden/__init__.py:14`).

6. **SaaS Features**:
   - Mount Admin Panel (see `eden/app.py:283-295`).
   - Integrate Mail (see `eden/app.py:108-112`).
   - Setup S3 Storage (see `README.md:212-219`).
   - Configure Stripe Payments (see `README.md:201-210`).

7. **Deployment**:
   - Docker configuration (multi-stage build).
   - Gunicorn/Uvicorn worker setup.
   - Environment variable management (`.env`).

## Output Requirements
1. **Save to `prompts.md`**: This enhanced prompt.
2. **Development Plan**: A step-by-step plan to write the tutorial, broken down by documentation sections.
