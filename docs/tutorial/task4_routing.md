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

### **Next Task**: [Implementing Premium UI with Templating](./task5_templating.md)
