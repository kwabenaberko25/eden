"""
════════════════════════════════════════════════════════════════════════════════
EDEN FRAMEWORK — COMPREHENSIVE GETTING STARTED GUIDE

Version: 1.0 (with Issues #29-44 fixes)
Last Updated: 2025

This guide covers:
1. What Eden is and what it's NOT
2. Quick Start (5 minutes)
3. Creating Your First Model
4. Database Migrations
5. Building Routes  
6. API Responses
7. Authentication
8. Templating (HTML)
9. Advanced Features

════════════════════════════════════════════════════════════════════════════════
PART 1: WHAT IS EDEN?

Eden is an async web framework for Python (built on Starlette/SQLAlchemy).

✅ What Eden Does:
- Async/await-first design (fast, modern)
- Django-like ORM for database queries
- Class-based and function-based views
- HTML templating with custom directives
- Dependency injection (FastAPI-style)
- Multi-tenant support (optional)
- Background task support
- API versioning

❌ What Eden Does NOT (and shouldn't):
- It's NOT Django (faster, more modern, but not compatible)
- It's NOT a drop-in Vue/React replacement (it's server-side MVC)
- It's NOT "Zero-Config" (you need basic setup; sorry for README!)
- It's NOT automatically secure (you must use @csrf_token, password hashing, etc.)
- It's NOT multi-tenant by default (you must opt-in with configuration)

Real Requirements:
- Python 3.10+
- PostgreSQL, MySQL, or SQLite
- ASGI server (Uvicorn, Hypercorn, etc.)
- Very basic Python web development knowledge

════════════════════════════════════════════════════════════════════════════════
PART 2: QUICK START (5 MINUTES)

1. Install Eden:

   pip install eden-framework
   pip install uvicorn  # ASGI server

2. Create a file `main.py`:

   from eden import Starlette
   from eden.db import Model, get_session
   from eden.db.fields import StringField, IntField
   from eden.responses import json
   from datetime import datetime
   from typing import Mapped
   
   # Initialize app
   app = Starlette()
   
   # Define a model
   class User(Model):
       __tablename__ = "users"
       name: Mapped[str] = StringField(max_length=100)
       email: Mapped[str] = StringField(max_length=254, unique=True)
       age: Mapped[int] = IntField(nullable=True)
   
   # Define a route
   @app.get("/")
   async def hello(request):
       users = await User.all()
       return json({"message": "Hello!", "users": len(users)})

3. Run it:

   uvicorn main:app --reload

4. Visit: http://localhost:8000/

That's it! Now let's make it real...

════════════════════════════════════════════════════════════════════════════════
PART 3: CREATING YOUR FIRST MODEL

Models represent database tables.

Step 1: Import What You Need

   from eden.db import Model
   from eden.db.fields import StringField, IntField, EmailField, DateTimeField, BoolField
   from datetime import datetime
   from typing import Mapped
   import uuid

Step 2: Define a Model

   class User(Model):
       __tablename__ = "users"
       
       # Primary key (auto)
       id: Mapped[uuid.UUID] = UUIDField(primary_key=True)
       
       # Required string fields
       name: Mapped[str] = StringField(max_length=100)
       username: Mapped[str] = StringField(max_length=50, unique=True, index=True)
       
       # Email (recommended: 254 chars per RFC 5321)
       email: Mapped[str] = StringField(max_length=254, unique=True)
       
       # Optional fields (nullable=True)
       bio: Mapped[str | None] = StringField(max_length=500, nullable=True)
       age: Mapped[int | None] = IntField(nullable=True)
       
       # Boolean with default
       is_active: Mapped[bool] = BoolField(default=True)
       
       # Timestamps (auto-managed)
       created_at: Mapped[datetime] = DateTimeField(auto_now_add=True)
       updated_at: Mapped[datetime] = DateTimeField(auto_now=True)

Available Field Types:

   StringField(max_length=...)         # max_length required
   TextField()                         # Unlimited text
   IntField()                          # Integer
   FloatField()                        # Decimal number
   BoolField(default=False)            # True/False
   DateTimeField(auto_now_add=True)    # Timestamp
   UUIDField(primary_key=True)         # UUID
   JSONField()                         # Structured data
   ForeignKeyField(...)                # Reference to another table

Step 3: Important Field Options

   StringField(
       max_length=100,        # REQUIRED for StringField
       nullable=False,        # Allow NULL (default: False)
       unique=True,           # Enforce uniqueness
       index=True,            # Create database index (speeds up queries)
       default="untitled"     # Default value
   )

Note on Defaults for StringField:
- Default max_length is 255 (safe for all DB vendors)
- For descriptions/content: use 1000 (still safe)
- For long text: use TextField() instead

Note on ID Conventions:
- UUID (recommended): Distributed systems, privacy-focused, slower queries
- Integer (recommended for single-server): Better performance, simpler URLs
- Choose ONE for your entire app and stick to it!

════════════════════════════════════════════════════════════════════════════════
PART 4: DATABASE MIGRATIONS

Migrations track schema changes. Use Alembic:

Step 1: Initialize Alembic

   alembic init migrations

Step 2: Configure database URL in alembic.ini

   sqlalchemy.url = postgresql+asyncpg://user:pass@localhost/dbname

Step 3: Create a migration

   # After defining a new model, create migration
   alembic revision --autogenerate -m "Add users table"

Step 4: Check the migration file (migrations/versions/xxxx_add_users_table.py)

   # Review it for accuracy

Step 5: Apply the migration

   alembic upgrade head

That's it! Your database is synced.

For development only (not production):

   # Drop all and recreate from models
   await Model.metadata.drop_all(engine)
   await Model.metadata.create_all(engine)

════════════════════════════════════════════════════════════════════════════════
PART 5: BUILDING ROUTES

Routes handle HTTP requests.

Basic GET Route:

   @app.get("/users/{user_id}")
   async def get_user(user_id: int):
       user = await User.get(user_id)
       if not user:
           return json({"error": True, "message": "Not found"}, status_code=404)
       return json(user.to_dict())

GET with Query Parameters:

   @app.get("/users")
   async def list_users(skip: int = 0, limit: int = 10):
       users = await User.offset(skip).limit(limit).all()
       return json([u.to_dict() for u in users])

POST Route (Create):

   @app.post("/users")
   async def create_user(request):
       data = await request.json()
       
       # Validate
       if not data.get("email"):
           return json(
               {"error": True, "message": "Email required"},
               status_code=400
           )
       
       # Create
       user = User(
           name=data.get("name"),
           email=data.get("email"),
           age=data.get("age")
       )
       await user.save()
       
       return json(user.to_dict(), status_code=201)

PUT/PATCH Route (Update):

   @app.patch("/users/{user_id}")
   async def update_user(user_id: int, request):
       data = await request.json()
       user = await User.get(user_id)
       
       if not user:
           return json({"error": True, "message": "Not found"}, status_code=404)
       
       # Update specific fields
       await user.update(
           name=data.get("name", user.name),
           email=data.get("email", user.email)
       )
       
       return json(user.to_dict())

DELETE Route:

   @app.delete("/users/{user_id}")
   async def delete_user(user_id: int):
       user = await User.get(user_id)
       if not user:
           return json({"error": True, "message": "Not found"}, status_code=404)
       
       await user.delete()  # Soft delete if model has SoftDeleteMixin
       return Response(status_code=204)  # No content

════════════════════════════════════════════════════════════════════════════════
PART 6: API RESPONSES

Always use consistent response format.

Success Response:

   return json({"id": 1, "name": "Alice"})  # HTTP 200

Created (201):

   return json(data, status_code=201)

Bad Request (400):

   return json(
       {"error": True, "message": "Email is required"},
       status_code=400
   )

Not Found (404):

   return json(
       {"error": True, "message": "User not found"},
       status_code=404
   )

Unprocessable (422 - validation error):

   return json(
       {
           "error": True,
           "code": "VALIDATION_ERROR",
           "errors": [
               {"field": "email", "message": "Invalid format"}
           ]
       },
       status_code=422
   )

════════════════════════════════════════════════════════════════════════════════
PART 7: AUTHENTICATION

Protect routes with authentication.

Step 1: Add password field to User model:

   from eden.security import hash_password, verify_password
   
   class User(Model):
       __tablename__ = "users"
       email: Mapped[str] = StringField(max_length=254)
       password_hash: Mapped[str] = StringField(max_length=255)
       auth_token: Mapped[str | None] = StringField(max_length=255, nullable=True)

Step 2: Create login route:

   @app.post("/auth/login")
   async def login(request):
       data = await request.json()
       email = data.get("email")
       password = data.get("password")
       
       user = await User.filter(email=email).first()
       
       if not user or not verify_password(password, user.password_hash):
           return json(
               {"error": True, "message": "Invalid credentials"},
               status_code=401
           )
       
       # Generate token
       token = secrets.token_urlsafe(32)
       await user.update(auth_token=token)
       
       return json({"token": token})

Step 3: Create dependency for protected routes:

   from eden.dependencies import Depends
   
   async def get_current_user(request):
       token = request.headers.get("Authorization", "").replace("Bearer ", "")
       if not token:
           return None
       user = await User.filter(auth_token=token).first()
       return user
   
   @app.get("/profile")
   async def get_profile(user=Depends(get_current_user)):
       if not user:
           return json(
               {"error": True, "message": "Not authenticated"},
               status_code=401
           )
       return json(user.to_dict())

════════════════════════════════════════════════════════════════════════════════
PART 8: TEMPLATING (HTML)

Render HTML templates.

Step 1: Create templates/base.html:

   <!DOCTYPE html>
   <html>
   <head>
       <title>{% block title %}Eden App{% endblock %}</title>
   </head>
   <body>
       {% block content %}{% endblock %}
   </body>
   </html>

Step 2: Create templates/users/list.html:

   {% extends "base.html" %}
   
   {% block title %}Users{% endblock %}
   
   {% block content %}
   <h1>Users</h1>
   <ul>
       {% for user in users %}
       <li>{{ user.name }} ({{ user.email }})</li>
       {% endfor %}
   </ul>
   {% endblock %}

Step 3: Render in route:

   from eden.templating import render_template
   
   @app.get("/users")
   async def list_users_html(request):
       users = await User.all()
       return render_template("users/list.html", users=users)

════════════════════════════════════════════════════════════════════════════════
PART 9: ADVANCED FEATURES

Transactions (@atomic):

   from eden.db import atomic
   
   @app.post("/transfer")
   @atomic   # All-or-nothing: commit or rollback
   async def transfer_money(request):
       data = await request.json()
       from_user = await User.get(data["from_id"])
       to_user = await User.get(data["to_id"])
       
       from_user.balance -= data["amount"]
       to_user.balance += data["amount"]
       
       await from_user.save()
       await to_user.save()

Query Optimization:

   # N+1 problem (bad)
   users = await User.all()
   for user in users:
       print(user.profile.bio)  # Query per user!
   
   # Fixed with prefetch
   users = await User.prefetch("profile").all()
   for user in users:
       print(user.profile.bio)  # Uses cached profile

Aggregation:

   from eden.db import Count, Avg
   
   stats = await User.aggregate(
       total_users=Count("id"),
       avg_age=Avg("age")
   )
   print(stats)  # {"total_users": 42, "avg_age": 32.5}

Pagination:

   page = await User.paginate(page=2, per_page=20)
   return json({
       "users": [u.to_dict() for u in page.items],
       "total": page.total,
       "next_url": page.links.get("next")
   })

════════════════════════════════════════════════════════════════════════════════
DEPLOYMENT CHECKLIST

Before going live:

☐ Set DEBUG=False in production
☐ Generate strong SECRET_KEY
☐ Use environment variables for credentials (DATABASE_URL, SECRET_KEY)
☐ Enable HTTPS (SSL/TLS)
☐ Use password hashing (verify_password, not plain text)
☐ Implement rate limiting for APIs
☐ Add logging for debugging
☐ Set up monitoring/alerting
☐ Test migrations on staging first
☐ Use connection pooling for database
☐ Enable CORS only for trusted domains
☐ Implement automated backups

════════════════════════════════════════════════════════════════════════════════
NEXT STEPS

Learn more:
- ORM: See eden/db/orm_reference.py
- DI: See eden/di_guide.py  
- API Standards: See eden/api_standards.py
- Field Helpers: See eden/db/field_helpers.py

Get help:
- GitHub: https://github.com/...
- Docs: https://eden.dev/docs
- Discord: https://discord.gg/...

════════════════════════════════════════════════════════════════════════════════
"""

# This is documentation. Save as docs/getting_started.md or similar.
