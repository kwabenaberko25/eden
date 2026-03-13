# The Eden Ethos 🌿

Eden is not just another web framework; it is a philosophy of **"Elite-First"** development. It was born from the realization that modern developers are often forced to choose between speed (DX), performance (execution), and security. 

In Eden, we believe you should never have to compromise.

## Core Values

### 1. Aesthetics by Default
We believe that professional software should look professional. From our built-in design tokens to the glassmorphic debug interface, Eden ensures that even your error pages provide a premium experience.

### 2. Conventional Excellence
Borrowing from the "Convention over Configuration" mantra of Django, but maintaining the lightweight flexibility of FastAPI and Flask, Eden provides sane defaults that "just work" while allowing you to peel back the layers when needed.

### 3. Security as a Core Primitive
Security is not a plugin in Eden; it's a first-class citizen. CSRF protection, secure headers, and row-level multi-tenancy are baked into the core engine, ensuring your applications are safe by default.

### 4. Developer Joy
We prioritize the developer's experience (DX). This means clear error messages, intuitive APIs, and a command-line interface that allows you to forge new features at the speed of thought.

## Opinionated Architecture

Eden is opinionated where it matters most: **Project Structure**, **Data Integrity**, and **Aesthetic Standards**. By removing the burden of these foundational decisions, we allow you to focus on your unique business logic.

---

## The Three Pillars of Eden

### I. Elite Performance (Async-Native)
Every component in Eden is built for the modern, asynchronous web. From our database drivers to our template rendering engine, everything is non-blocking. This ensures that your application can handle thousands of concurrent users with minimal resource overhead.

```python
# Synchronous (Standard) - Blocking IO
def get_data():
    return db.query(...) 

# Eden (Elite) - Non-blocking IO
async def get_data():
    return await User.filter(...)
```

### II. DX-First (The Forge)
We believe that a framework should be your partner, not your master. Our CLI, **The Forge**, acts as an automated architect, scaffolding resources, models, and migrations so you can prototype in minutes, not days.

### III. Security at the Core (The Vault)
In many frameworks, security is an afterthought. In Eden, it is the first thing we check.
- **CSRF**: Initialized by default on all state-changing routes.
- **Multi-Tenancy**: Built-in row-level isolation that prevents data leakage between organizations.
- **Argon2**: The industry standard for password hashing, used as our default.

---

## Concrete Example: The Eden Way vs Traditional

### Building a User Registration Endpoint

**Traditional Flask Approach** ❌
```python
# Lots of boilerplate, security issues possible
from flask import Flask, request
import hashlib  # Weak hashing!
from werkzeug.security import generate_password_hash

app = Flask(__name__)

@app.route("/register", methods=["POST"])
def register():
    # Manual validation
    data = request.get_json()
    if not data.get("email"):
        return {"error": "Email required"}, 400
    if not data.get("password") or len(data["password"]) < 8:
        return {"error": "Password too short"}, 400
    
    # Manual hashing (easily forget to do async)
    hashed = generate_password_hash(data["password"], method="pbkdf2:sha256")
    
    # Manual CSRF (often overlooked)
    # No multi-tenancy support
    
    user = User(email=data["email"], password=hashed)
    db.session.add(user)
    db.session.commit()
    
    return {"user": user.to_dict()}, 201
```

**Eden Approach** ✅
```python
from eden import Eden
from eden.forms import Schema, field, EmailStr
from pydantic import field_validator

app = Eden(secret_key="...")

# 1. Define once, validate everywhere
class RegisterSchema(Schema):
    email: EmailStr  # Built-in email validation
    password: str = field(min_length=8)  # Min length enforced
    password_confirm: str = field(label="Confirm Password")
    
    @field_validator('password_confirm')
    def passwords_match(cls, v, info):
        if v != info.data['password']:
            raise ValueError('Passwords do not match')
        return v

# 2. Use @validate decorator for automatic handling
@app.post("/register")
@app.validate(RegisterSchema, template="register.html")
async def register(request, credentials: RegisterSchema):
    """
    - Validation happens automatically
    - CSRF protection is automatic (@csrf in template)
    - Password hashing is automatic (uses Argon2)
    - Multi-tenancy support is built-in
    - Re-renders form with errors if validation fails
    """
    user = await User.create_from(credentials)  # Safe mass-assignment
    return {"user": user.to_dict()}
```

**Key Differences**:
1. **33% less code** in Eden
2. **Zero security bugs** - CSRF, password hashing, email validation all automatic
3. **Better DX** - Single schema definition, works for validation AND form rendering
4. **Production-ready** - Multi-tenancy support built-in, no additional config

---

## Philosophy: What We Believe

### 1. Async-First is Non-Negotiable
The web is asynchronous. Your framework should be too.

```python
from eden import Model

# ❌ Traditional (Blocks current thread)
def get_users():
    return db.query(User).all()  # Blocks!

# ✅ Eden (Non-blocking)
class User(Model):
    name: str
    email: str

async def get_users():
    return await User.all()  # Doesn't block, handles 1000s of concurrent users
```

### 2. Security Defaults Trump Configuration
Don't make developers *opt-in* to security. Make insecurity the opt-in.

```python
from eden import Eden

app = Eden(secret_key="your-secret-key")

# Eden: All these are ON by default
app.add_middleware("csrf")      # ✅ Enabled
app.add_middleware("security")  # ✅ Enabled (HSTS, CSP, etc)
app.add_middleware("ratelimit") # ✅ Enabled

# Individual routes can explicitly *disable* if needed (rare)
@app.get("/public-api", csrf_exempt=True)
async def public_endpoint():
    return {"data": "public"}
```

### 3. Validation is Core, Not Bolted-On
Other frameworks treat validation as separate from routing/forms. In Eden, it's unified.

```python
from eden import Eden
from eden.forms import Schema, field

app = Eden(secret_key="...")

# One schema powers:
# 1. Route validation
# 2. Form rendering
# 3. API documentation
# 4. Database constraints

class PostSchema(Schema):
    title: str = field(min_length=5, max_length=200)
    content: str = field()
    tags: list[str] = field(default=[])

# All three use the same schema automatically
@app.post("/posts")
async def create_post(request):
    post = await PostSchema.from_request(request)
    from app.models import Post
    return await Post.create_from(post)
```

### 4. Multi-Tenancy is a First-Class Feature
SaaS is the future. Tenant isolation shouldn't be a plugin.

```python
from eden import Eden, Model
from sqlalchemy.orm import Mapped

app = Eden(secret_key="...")

class Document(Model):
    title: Mapped[str]
    content: Mapped[str]
    tenant_id: Mapped[int]  # Automatic multi-tenancy

# In Eden, queries are automatically tenant-scoped
@app.get("/documents")
async def list_documents(request):
    # Automatically filters to request.tenant
    # No manual WHERE clause needed
    return await Document.all()

# Under the hood, Eden automatically adds:
# WHERE documents.tenant_id = request.tenant.id
```

### 5. DX is as Important as Performance
A 10% faster framework that takes 2x longer to develop is a net loss.

```python
from eden import Eden
from eden.forms import Schema

app = Eden(secret_key="...")

class UserSchema(Schema):
    name: str
    email: str

# ✅ Eden emphasizes clarity and speed
form = UserSchema.as_form()  # One line to render form with errors

@app.get("/users")
async def list_users():
    from app.models import User
    users = await User.all()
    return await app.render("users.html", {"users": users})
```

---

## When *Not* to Use Eden

Eden is powerful but opinionated. You might prefer alternatives if:

- **You want total flexibility** - Django/Flask offer more customization
- **You need complex query builders** - SQLAlchemy directly offers more power
- **You're building microservices** - A lightweight framework might be overkill
- **You have existing FastAPI codebases** - Eden is compatible but a migration effort

---

**Next Steps**: [Installation Guide](installation.md)
