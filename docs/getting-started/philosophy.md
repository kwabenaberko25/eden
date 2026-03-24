# The Eden Ethos 🌿

**Eden is not just another web framework; it is a philosophy of "Elite-First" development.**

Born from the friction of modern web architecture, Eden was designed for the developer who refuses to choose between **speed (DX)**, **industrial performance**, and **impenetrable security**. In Eden, we believe you should never have to compromise.

---

## 🏛️ The Three Pillars of Eden

### I. Industrial Performance (Async-Native)

Every line of Eden is built for the modern, asynchronous web. From our database drivers to our template rendering engine, everything is non-blocking. This ensures your application handles thousands of concurrent users with the grace of a specialized monolith.

```python
from eden import Model, f, Mapped

class User(Model):
    is_active: Mapped[bool] = f(default=True)

async def get_active_users():
    # Eden supports clean ActiveRecord selection
    return await User.select().where(User.is_active == True).all()
```

### II. The Forge (Developer Joy)

We believe a framework should be your architect, not your master. Our CLI, **The Forge**, acts as an automated partner—scaffolding resources, models, and migrations so you can move from "Idea" to "Production" at the speed of thought.

### III. The Vault (Security as a Primitive)

In Eden, security is not a plugin; it is a first-class citizen. CSRF protection, secure headers, and row-level multi-tenancy are baked into the core engine. Your applications are safe before you even write your first route.

---

## 💎 Core Values

### 🎨 Aesthetics by Default

Professional software should look professional. From built-in design tokens to the glassmorphic debug interface, Eden ensures your project feels premium from day one.

### 📜 Conventional Excellence

We follow "Convention over Configuration," but without the "magic" that obscures logic. Eden provides sane, high-performance defaults that "just work," while giving you the hooks to peel back layers when needed.

### 🛡️ Secure by Design

Security isn't a checkbox; it's the foundation. Argon2 password hashing, automatic CSRF, and strict tenant isolation are not optional additions—they are the heart of the framework.

---

## ⚡ The Eden Difference

| Feature | Legacy Frameworks | The Eden Way |
| :--- | :--- | :--- |
| **IO Model** | Often Sync/Mixed | **100% Async-Native** |
| **Security** | Manual/Opt-in | **The Vault (Automatic)** |
| **Frontend** | Separate SPA / Heavy JS | **HTMX Fragments (unified)** |
| **Multi-Tenancy** | Hand-rolled / Risky | **Built-in Isolation** |
| **Database** | Heavy Migrations | **Automatic Evolution** |

---

## 🔬 Contrast: Traditional vs. Eden

### User Registration Pattern

**Traditional Approach** ❌ (Boilerplate-heavy, manual security)

```python
from unittest.mock import MagicMock
from eden import Eden, Request, Model
app = Eden(secret_key="dev-secret")
class User(Model): pass
db = MagicMock() # Mock SQLAlchemy db for illustration

# Manual validation, weak hashing, no N+1 protection
@app.route("/register", methods=["POST"])
async def register(request: Request):
    data = await request.json()
    if not data.get("email"): return {"error": "Email required"}, 400
    
    # Mocking hashed password for illustration
    hashed = data["password"] + "_hashed" 
    user = User(email=data["email"], password=hashed)
    # Manual DB session handling
    async with db.session() as session:
        session.add(user)
        await session.commit()
    return {"user": user.to_dict()}, 201
```

**The Eden Way** ✅ (Unified, secure, high-performance)

```python
from eden import Eden, Model, f, Mapped
from eden.forms import Schema, field, EmailStr

app = Eden(secret_key="dev-secret")

class User(Model):
    email: Mapped[str] = f(unique=True)

class RegisterSchema(Schema):
    email: EmailStr
    password: str = field(min_length=8)

@app.post("/register")
@app.validate(RegisterSchema)
async def register(request, credentials: RegisterSchema):
    # Validation, CSRF, and Password Hashing are all handled automatically
    user = await User.create(email=credentials.email, password=credentials.password)
    return {"user": user.to_dict()}
```

---

## 🧠 Philosophy: What We Believe

### 1. Multi-Tenancy is Not a Plugin

SaaS is the default mode of modern software. Tenant isolation shouldn't be a library you find on GitHub; it should be the air your application breathes.

```python
from eden import Model, f, Mapped

class Document(Model):
    title: Mapped[str] = f()
    tenant_id: Mapped[int] = f() # Automatically scoped by the engine
```

### 2. Validation is the Source of Truth

One schema should power your API validation, your form rendering, and your database constraints. Why define your data structure three times?

### 3. The "Unified Context"

The wall between the Backend and the Frontend is a relic of the past. Eden's **HTMX-powered Fragments** allow you to build interactive, stateful UIs without leaving the Python ecosystem.

---

## 🚫 When *Not* to Use Eden

Eden is powerful but opinionated. You might prefer specialized alternatives if:

- **Total Flexibility**: If you need to manually manage every byte of the HTTP socket, a low-level library like Starlette or raw Flask might be better.
- **Deep SQL Specialization**: For recursive CTEs or extreme window function logic, you can drop to raw SQLAlchemy within Eden, but the framework is optimized for **Industrial Web Patterns**.
- **Legacy Migrations**: If you are tied to a manual, hand-written migration history that cannot be mapped to Eden's automated evolution engine.

---

### 🚀 Next Steps

Ready to build something elite? [Install the Eden Core](installation.md) or dive into the [Quick Start Guide](quickstart.md).
