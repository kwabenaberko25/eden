# Task 4: Build HTTP Routes & Views

**Goal**: Handle incoming HTTP requests, process data, and return structured responses using Eden's modular routing system.

---

## 🛣️ Step 4.1: Creating a Modular Router

Eden's `Router` allows you to group related handlers into a single module, keeping your project organized and maintainable.

**File**: `app/routes/user.py`

```python
from eden import Router
from app.models import User

# Initialize the router with a namespace name
user_router = Router(name="users")

@user_router.get("/", name="list")
async def list_users():
    """Return a JSON list of all users."""
    users = await User.all()
    # Eden automatically handles list/dict to JSON conversion
    return [user.to_dict() for user in users]
```

### Registering the Router
To make these routes active, we must include them in the **Main Router**:

**File**: `app/routes/__init__.py`
```python
from .user import user_router

main_router.include_router(user_router, prefix="/users")
```

Now, your routes are available at `http://127.0.0.1:8000/users/`. 

Because you named the router `users` and the route `list`, Eden automatically creates the reverse route `users:list`. 
In your HTML templates, you can link to this route natively using:
`<a href="@url('users:list')">View Users</a>`

---

## ⚡ Step 4.2: Dynamic Parameters & Type Safety

Eden supports flexible path parameters with automatic type conversion.

```python
from eden import Response, status

@user_router.get("/{user_id}")
async def get_details(user_id: int):
    """Fetch a single user by their ID."""
    user = await User.get(id=user_id)
    
    if not user:
        return Response(
            {"error": "User not found"}, 
            status_code=status.HTTP_404_NOT_FOUND
        )
        
    return user.to_dict()
```

### 🧠 What's happening?

- `{user_id}`: Captures the value from the URL.
- `: int`: Eden ensures the incoming string is converted to an integer before reaching your code.

---

## 📥 Step 4.3: Handling Post Data (Mutations)

When building APIs, you'll need to handle incoming JSON payloads or form data.

```python
from eden import Request

@user_router.post("/")
async def create_new(request: Request):
    """Create a new user from JSON data."""
    # Efficiently parse incoming JSON
    data = await request.json()
    
    # Delegate to ORM
    new_user = await User.create(**data)
    
    return Response(
        new_user.to_dict(), 
        status_code=status.HTTP_201_CREATED
    )
```

> [!TIP]
> Eden's `Request` object is a supercharged version of Starlette's request, providing easier data access methods like `request.json()` and `request.form()`.

---

## 🔄 Step 4.4: Update & Delete Operations

Complete your CRUD implementation with update and delete handlers:

```python
@user_router.put("/{user_id}")
async def update_user(request: Request, user_id: int):
    """Update an existing user with new data."""
    data = await request.json()
    
    user = await User.get(id=user_id)
    if not user:
        return Response(
            {"error": "User not found"}, 
            status_code=status.HTTP_404_NOT_FOUND
        )
    
    # Update only provided fields
    await user.update(**data)
    
    return {
        "message": "User updated successfully",
        "user": user.to_dict()
    }

@user_router.delete("/{user_id}")
async def delete_user(user_id: int):
    """Remove a user permanently."""
    user = await User.get(id=user_id)
    if not user:
        return Response(
            {"error": "User not found"}, 
            status_code=status.HTTP_404_NOT_FOUND
        )
    
    await user.delete()
    return Response(
        {"message": "User deleted"}, 
        status_code=status.HTTP_204_NO_CONTENT
    )
```

---

## ✅ Step 4.5: Request Validation with Schemas

Use Pydantic schemas to automatically validate incoming data:

```python
from pydantic import BaseModel, EmailStr

class UserCreateRequest(BaseModel):
    name: str  # Required
    email: EmailStr  # Validated email format
    age: int | None = None  # Optional

@user_router.post("/")
async def create_user_validated(request: Request):
    """Create a user with automatic validation."""
    try:
        data = await request.json()
        validated = UserCreateRequest(**data)  # Pydantic validates here
    except ValueError as e:
        return Response(
            {"error": f"Invalid input: {str(e)}"}, 
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    new_user = await User.create(**validated.dict())
    return Response(
        new_user.to_dict(),
        status_code=status.HTTP_201_CREATED
    )
```

> [!TIP]
> Eden recommends using the `@app.validate` decorator (shown in Task 6) for cleaner form handling in web routes.

---

## 🎯 Step 4.6: Sub-Routers & Organization

For larger applications, organize routes into logical modules:

```python
# app/routes/__init__.py
from eden import Router
from .user import user_router
from .post import post_router
from .admin import admin_router

main_router = Router()
main_router.include_router(user_router, prefix="/users", name="users")
main_router.include_router(post_router, prefix="/posts", name="posts")
main_router.include_router(admin_router, prefix="/admin", name="admin")
```

Now your routes are:
- `/users/` (list users)
- `/users/{user_id}` (get user)
- `/posts/` (list posts)
- `/admin/metrics` (admin dashboard)

**Named routes** make templating cleaner:
```html
<a href="@url('users:list')">All Users</a>
<a href="@url('posts:list')">All Posts</a>
```

---

### **Next Task**: [Implementing Premium UI with Templating](./task5_templating.md)
