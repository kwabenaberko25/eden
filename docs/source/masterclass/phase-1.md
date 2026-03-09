# Phase 1: The Seed (Philosophy & First Steps) 🌿

Welcome to the **Eden Masterclass**. This tutorial will take you from an absolute beginner to an elite developer capable of deploying production-grade, multi-tenant applications using the Eden Framework. 

By the end of this journey, you will have built a comprehensive application (the "SuperTask" hub) leveraging Eden's most powerful features.

---

## 🌌 The Eden Philosophy: Why Another Framework?

You might be asking: *Why do we need another framework when we have Django, FastAPI, and Flask?*

Eden was born from a specific need: developers want **Django's batteries-included features**, **FastAPI's modern async speed and typing**, and **Flask's elegant simplicity**, all without the headache of gluing thirty different libraries together.

Unlike other frameworks, Eden provides a **unique synergy** out of the box:
1. **Built-in Multi-Tenancy:** True data isolation and subdomain routing natively supported—no hacking middleware required.
2. **The HTMX + Pydantic Synergy:** Build dynamic, reactive, Single-Page Application (SPA) experiences using pure Python and HTML, heavily relying on Pydantic for bulletproof forms.
3. **Advanced `ResourceModel` ORM:** Skip the boiler-plate CRUD operations entirely.
4. **Security-First:** Row-level RBAC (Role-Based Access Control) enforced deeply at the database and routing levels.

Eden assumes you are building a modern SaaS. It gives you the "Premium" tools—like background tasks, Stripe billing, and WebSockets—from minute one.

---

## 🛠️ Installation & Project Anatomy

To begin, we recommend using `uv` for lightning-fast dependency management, though standard `pip` works perfectly fine.

### 1. Installation

Install the Eden Framework globally or in your virtual environment:

```bash
uv pip install eden-framework
```

### 2. Scaffolding Your First Project

Eden comes with a powerful CLI. Let's use it to generate a professional, Docker-ready project structure. Open your terminal and run:

```bash
eden new my_app
```

The wizard will ask you to select your database engine (e.g., SQLite, PostgreSQL). For this tutorial, selecting `sqlite` is perfectly fine, though PostgreSQL is the standard for production.

Let's navigate into the generated directory:

```bash
cd my_app
```

### 3. Understanding the "Elite" Anatomy

The `eden new` command creates a pristine, production-ready structure. Here is where everything lives:

* **`app/__init__.py`**: *The Eden Heart.* This is where your application is instantiated, middleware is mounted, and routes are gathered.
* **`app/settings.py`**: Your configuration registry. It handles environment variables, database connections, and security settings safely.
* **`app/routes/`**: *Modular Sector Control.* Contains your API and view routing logic.
* **`app/models/`**: *The Data Forge.* Where your database entities (Tables) are defined.
* **`templates/` & `static/`**: Your premium UI layer. Eden uses a powerful directive-based templating engine here.
* **`docker-compose.yml` & `Dockerfile`**: Production-ready container configurations supplied out of the box.

---

## 🚦 Requests, Responses, & Routing

Let's understand how Eden handles web traffic. The routing system in Eden is designed to be frictionless. 

Let's look at a basic route definition (typically found in `app/routes/__init__.py` or similar):

```python
from eden import Router

main_router = Router()

@main_router.get("/")
async def index():
    return {"message": "Welcome to Eden! 🌿"}
```

### The Conversational Insight: "Aha!" Moments in Routing

If you are coming from other frameworks, you might wonder: *How does this router map so cleanly, and why is there so little boilerplate?*

1. **Automatic Serialization:** Notice how the `index()` function returns a standard Python dictionary? Eden seamlessly and automatically detects standard data structures (`dict`, `list`) and instantly wraps them in an optimized `JsonResponse` under the hood. You rarely need to explicitly instantiate `Response` objects unless you are doing something highly custom.
2. **Decorator-Driven:** The `@main_router.get("/")` decorator directly binds the HTTP GET method to your asynchronous Python function. You can just as easily use `@main_router.post`, `@main_router.delete`, etc.
3. **Path Parameters:** Extracting variables from URLs is statically typed and effortless:

```python
@main_router.get("/users/{user_id:int}")
async def get_user(user_id: int):
    # 'user_id' is automatically validated as an integer!
    return {"id": user_id, "name": "Secure Sector Alpha"}
```

If a user visits `/users/abc`, Eden will automatically handle the validation error and return a clean 422 Unprocessable Entity response—you don't write *any* parsing code.

### Rendering the UI Layer (HTML)

While APIs are great, Eden excels at rendering UIs. 

```python
from eden import request  # Eden magic: Context-aware request access

@main_router.get("/dashboard")
async def dashboard():
    # request() automatically fetches the current Request object contexts.
    # The application instance (`request.app`) easily renders templates.
    
    # We pass 'context' data safely to the template.
    return request.app.render("dashboard.html", {"title": "Admin View"})
```

We will explore templates deeply in Phase 3, but this shows the immediate, clean handoff from a route to the frontend.

---

## 🚀 Launching the Application

Let's verify your foundation. Launch the built-in development server utilizing the CLI:

```bash
eden run
```

You should see an output indicating the server is running (typically on `http://127.0.0.1:8000`).
Visit that URL in your browser, and you should see the JSON welcome message.

---

### 🎉 Phase 1 Complete

You have successfully installed the framework, scaffolded a production-ready application, and comprehended how Eden naturally handles HTTP routing.

Your foundation is **100% Verified**. You are ready to step into the database layer.

**Up Next: [Phase 2: The Soil (Data & Modeling)](./phase-2.md)**
