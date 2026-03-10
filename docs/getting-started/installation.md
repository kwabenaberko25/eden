# Installation 🛠️

Setting up Eden is straightforward. We recommend using a virtual environment to keep your project dependencies isolated.

## Prerequisites

- **Python**: 3.11 or higher.
- **Node.js** (Optional): Required if you want to use the `npx eden` scaffolding tools.

## Standard Installation

You can install the Eden Framework directly from PyPI:

```bash
pip install eden-web
```

Or using **uv** (recommended for speed):

```bash
uv add eden-web
```

## Creating a New Project (Scaffolding)

The fastest way to start a new Eden project with the recommended structure is using the `npx` command:

```bash
npx eden new my_future_app
```

This command will:
1. Create a new directory named `my_future_app`.
2. Generate a standard project structure.
3. Set up a local SQLite database configuration.
4. Create an initial `app.py`.

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
   pip install eden-web
   ```

---

**Next Steps**: [Quick Start Guide](quickstart.md)
