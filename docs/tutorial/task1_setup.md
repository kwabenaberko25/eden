# Task 1: Environment Setup & Scaffolding

**Goal**: Create a professional development environment and generate the standard Eden project structure.

---

## 🚀 Step 1.1: Create Project Directory

Open your terminal and create a dedicated folder for your new application.

```bash
mkdir my_eden_app
cd my_eden_app
```

> [!TIP]
> Use a descriptive name in snake_case to avoid issues with package naming later.

---

## 📦 Step 1.2: Set Up Virtual Environment

Isolate your project dependencies to ensure a clean, reproducible environment.

### Option A: Using `uv` (Recommended)
`uv` is an extremely fast Python package and project manager.

```bash
# Windows
uv venv
.venv\Scripts\activate

# macOS / Linux
uv venv
source .venv/bin/activate
```

### Option B: Using Standard Python
If you prefer standard tools:

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS / Linux
python -m venv .venv
source .venv/bin/activate
```

---

## 🌿 Step 1.3: Install Eden Framework

Install the framework from PyPI or your local development source.

### Option A: From PyPI (Standard)
```bash
pip install eden-framework
```

### Option B: From Local Source (Development)
If you are contributing to the framework:
```bash
pip install -e C:\ideas\eden
```

### 🔍 Verification

Confirm the installation:
```bash
# Windows
pip list | findstr eden-framework

# macOS / Linux
pip list | grep eden-framework
```
**Expected Output**: `eden-framework 0.1.0`

---

## 🛠️ Step 1.4: Scaffold Project with CLI

Use the built-in `eden` command to generate a production-ready project structure.

```bash
eden new my_eden_app
```

### Interactive Prompt
Select **SQLite** for this tutorial (it's zero-config).

```text
🗄️  Select Database Engine [sqlite]:
```

### Generated Structure Overview
Eden scaffolds a structured layout designed for scalability:

```text
my_eden_app/
├── app/
│   ├── __init__.py      # App factory & configuration
│   ├── models/          # Database entities
│   ├── routes/          # API & Web handlers
│   └── settings.py      # Environment-based settings
├── static/              # Public assets (CSS, JS, Images)
├── templates/           # Premium UI templates
├── tests/               # Test suite (Pytest ready)
├── Dockerfile           # Production container build
├── docker-compose.yml   # Dev services (DB, Cache)
└── requirements.txt     # Dependency list
```

---

## ⚡ Step 1.5: Finalize Installation

Install the required dependencies generated in your new project.

```bash
pip install -r requirements.txt
```

> [!IMPORTANT]
> This installs `uvicorn` (the server), `pytest`, and all necessary drivers for your selected database.

---

### **Next Task**: [Configuring the Application Core](./task2_core.md)
