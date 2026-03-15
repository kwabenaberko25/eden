# Dependency Injection 🔧

Eden includes a built-in dependency injection system that works seamlessly with async/await. This guide covers advanced dependency patterns.

## Overview

Dependencies allow you to:
- Access shared resources (database sessions, config, cache)
- Validate request parameters before reaching your handler
- Inject mocked dependencies in tests
- Keep handlers clean and focused

## Basic Dependency

```python
from eden.dependencies import Depends

async def get_current_user(request):
    """Extract and validate user from request."""
    user_id = request.session.get("user_id")
    if not user_id:
        raise Exception("Not authenticated")
    return await User.get(user_id)

@app.get("/profile")
async def profile(user = Depends(get_current_user)):
    """User parameter is automatically injected."""
    return {"user": user.to_dict()}
```

## Parametrized Dependencies

```python
async def get_paginated(
    page: int = 1,
    limit: int = 20
):
    """Pagination dependency."""
    offset = (page - 1) * limit
    return {"offset": offset, "limit": limit}

@app.get("/posts")
async def list_posts(paginate = Depends(get_paginated)):
    posts = await Post.all().offset(
        paginate["offset"]
    ).limit(
        paginate["limit"]
    )
    return {"posts": [p.to_dict() for p in posts]}
```

## Dependency Caching

Dependencies are cached per request to avoid redundant computations:

```python
async def get_db_connection():
    """Expensive database operation - only called once per request."""
    return await database.connect()

@app.get("/data")
async def data(db = Depends(get_db_connection)):
    # All dependencies in this handler share the same db connection
    return {"data": "..."}
```
