# Installation 🛠️

Setting up Eden is straightforward. We recommend using a virtual environment to keep your project dependencies isolated.

## Prerequisites

- **Python**: 3.11 or higher.
- **Node.js** (Optional): Only required if you plan to use advanced asset pipelines (e.g., Vite/Tailwind) or specific `npx` execution wrappers.

## Standard Installation

You can install the Eden Framework directly from PyPI:

```bash
pip install eden-framework
```

```bash
uv add eden-framework
```

## Creating a New Project (Scaffolding)

The recommended way to start a new Eden project is using the native `eden new` command:

```bash
# 1. Install eden-framework (Standard)
pip install eden-framework

# 2. Use the native scaffolding tool
eden new my_future_app
```

This command will:
1. Create a new directory named `my_future_app`.
2. Generate a standard project structure (Models, Routes, Components).
3. Set up a local SQLite database configuration.
4. Create an initial `app.py` and Docker configuration.

> [!TIP]
> You can also use `uv run eden-framework new project_name` if you prefer to avoid global installations.

## Manual Setup

If you prefer to build your project from scratch:

1. Create a new directory:

   ```bash
   mkdir eden_app && cd eden_app
   ```

2. Set up a virtual environment:

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install Eden:

   ```bash
   pip install eden-framework
   ```

---

**Next Steps**: [Quick Start Guide](quickstart.md)
