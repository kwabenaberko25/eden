# 🛠️ Installation & Setup

**Setting up Eden is a professional, high-fidelity experience designed to get you from a blank terminal to a production-ready application in under 60 seconds.**

---

## ⚡ The 60-Second Start

If you're already in a virtual environment, run this to bootstrap a standard SaaS project:

```bash
pip install eden-framework[all]
eden new my-project --profile=standard
cd my-project
eden run
```

---

## 📋 Prerequisites

Before you begin, ensure your environment meets these professional specifications:

- **Python 3.11+**: Optimized for the latest `asyncio` performance features (3.12+ recommended).
- **Virtual Environment**: Isolation is non-negotiable for industrial stability.
- **Terminal**: A modern terminal with UTF-8 support (for Eden's rich CLI output).

---

## 🚀 Installation Tiers

Eden is modular by design. You only pull in what your architecture requires.

### 1. The Core (Minimalist)

Ideal for microservices or lightweight proxies where every byte counts.
```bash
pip install eden-framework
```

### 2. The Data Tier (Standard)

Adds asynchronous drivers for **PostgreSQL** and **MySQL**.
```bash
pip install eden-framework[databases]
```

### 3. The Elite Suite (Full-Stack)

The recommended choice for building SaaS products. Includes **Stripe**, **AWS S3**, **Redis Caching**, **Background Workers**, and **Email**.
```bash
pip install eden-framework[all]
```

---

## 🏗️ Manual Setup

For architects who prefer a custom foundation, follow this manual sequence:

### 1. Environment Isolation

```bash
mkdir my-eden-app && cd my-eden-app
python -m venv .venv

# On Windows: .venv\Scripts\activate

source .venv/bin/activate
```

### 2. Initialize the Entry Point

Create an `app.py` file with the following high-performance boilerplate:

```python
from eden import Eden

app = Eden(
    title="Elite Core Service",
    debug=True,
    secret_key="change-this-for-production"
)

@app.get("/")
async def index():
    return {"status": "Eden Architecture Active 🌿"}
```

---

## 🛡️ Verification Check

Execute these diagnostics to verify your engine is correctly tuned:

```bash

# Verify Framework Presence

python -c "import eden; print(f'Eden Version: {eden.__version__}')"

# Verify SQL Engine

python -c "import sqlalchemy; print('Alchemy 2.0+ Active')"

# Verify CLI Integration

eden info
```

---

## 💡 Elite Tips & Best Practices

- **Variable Sync**: Use a `.env` file from Day 1. Eden automatically detects it and populates your `app.config`.
- **Driver Selection**: For local development, `aiosqlite` is pre-configured. Switch to `asyncpg` for PostgreSQL in your staging environment.
- **Global CLI**: While we recommend installing Eden in a virtual environment, you can install the standalone `eden-forge` package globally to manage your projects across different environments.

---

### 🚀 Next Steps

Now that your engine is running, dive into the [Quick Start Guide](quickstart.md) or explore the [Framework Philosophy](philosophy.md).
