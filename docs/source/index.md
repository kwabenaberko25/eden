# 🌿 Eden Framework Documentation

Welcome to the **Eden Framework** documentation. This is your comprehensive guide to mastering Eden—a high-performance, asynchronous Python web framework that combines **Django's features**, **FastAPI's speed**, and **Flask's simplicity**.

---

## Quick Navigation

```{toctree}
:maxdepth: 2

intro/index
cli/index
```

---

## 🎓 The Eden Masterclass (Premium)

A deep-dive journey from the philosophy of Eden to deploying a production-grade, multi-tenant SuperTask hub.

```{toctree}
:caption: Eden Masterclass
:maxdepth: 2
:numbered:

masterclass/phase-1
masterclass/phase-2
masterclass/phase-3
masterclass/phase-4
masterclass/phase-5
masterclass/phase-6
masterclass/phase-7
```

---

## 🚀 The 15-Phase Learning Journey (Standard)

Follow the modular phases below to build your application from the ground up.

```{toctree}
:caption: Standard Tutorial
:maxdepth: 2
:numbered:

phase1
phase2
phase3
phase4
phase5
phase6
phase7
phase8
phase9
phase10
phase11
phase12
phase13
phase14
phase15
```

---

## 📚 Reference Documentation

```{toctree}
:maxdepth: 2

api_reference
```

---

## 🛰️ Architecture Overview

Eden is architected around the principle of **Modular Excellence**. Every component, from the core ASGI heart to the Data Forge, is designed to be isolated yet perfectly synchronized.

| Feature | Component | Eden implementation |
| :--- | :--- | :--- |
| **Routing** | `Resource` | Automatic class-based routing |
| **Modeling** | `Model` | Pydantic-powered ORM |
| **Logic** | `Eden` | The central application engine |
| **Auth** | `RBAC` | Enterprise-grade access control |
| **UI** | `Template` | Jinja2, Forms, Components |
| **Admin** | `AdminPanel` | Auto-generated admin interface |
| **Integrations** | `Service` | Payments, Storage, Email, Tasks |

---

## Getting Started

### Installation

```bash
eden new colony_manager
cd colony_manager
uv run uvicorn Eden:app --reload
```

### Your First App

```python
from eden import Eden

app = Eden\(title="My App")

@app.get("/")
async def hello():
    return {"message": "Hello, Eden!"}

app.run()
```

Run with:

```bash
eden run
```

---

## Key Features

- **Async-First**: Built on Starlette for high performance
- **Type Safety**: Full Pydantic v2 integration
- **Database**: SQLAlchemy 2.0 with async support
- **Security**: Built-in RBAC, CSRF, and multi-tenancy
- **DX**: Hot reload, beautiful error pages, CLI tooling

---

## Community & Support

- **GitHub**: [Eden on GitHub](https://github.com/eden-framework/eden)
- **Issues**: [Support & Issues](https://github.com/eden-framework/eden/issues)

