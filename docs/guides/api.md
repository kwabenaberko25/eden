# API Best Practices 🎯

Build scalable, RESTful APIs with Eden. This guide covers design patterns, versioning, and common best practices.

## REST Principles

### Resource-Oriented Design

Structure your routes around resources, not actions:

```python
# ✅ CORRECT: Resource-oriented
@app.get(\"/users\")
async def list_users():
    return await User.all()

@app.post(\"/users\")
async def create_user(request):
    data = await request.json()
    user = await User.create(**data)
    return user

@app.get(\"/users/{user_id}\")
async def get_user(user_id: int):
    return await User.get(user_id)

@app.put(\"/users/{user_id}\")
async def update_user(request, user_id: int):
    data = await request.json()
    user = await User.get(user_id)
    await user.update(**data)
    return user

@app.delete(\"/users/{user_id}\")
async def delete_user(user_id: int):
    user = await User.get(user_id)
    await user.delete()
    return {\"deleted\": True}

# ❌ WRONG: Action-oriented
# @app.get(\"/users/get_user\")
# @app.post(\"/users/create_user\")
# @app.post(\"/users/update_user\")
```

### Status Codes

Use appropriate HTTP status codes:

```python
from starlette.responses import JSONResponse

@app.post(\"/users\")
async def create_user(request):
    try:
        data = await request.json()
        user = await User.create(**data)
        return JSONResponse(user.to_dict(), status_code=201)  # Created
    except ValueError as e:
        return JSONResponse({\"error\": str(e)}, status_code=400)  # Bad Request

@app.get(\"/users/{user_id}\")
async def get_user(user_id: int):
    user = await User.get(user_id)
    if not user:
        return JSONResponse({\"error\": \"Not found\"}, status_code=404)
    return user.to_dict()

@app.delete(\"/users/{user_id}\")
async def delete_user(user_id: int):
    user = await User.get(user_id)
    if not user:
        return JSONResponse({\"error\": \"Not found\"}, status_code=404)
    await user.delete()
    return JSONResponse({\"deleted\": True}, status_code=204)  # No Content
```

## API Versioning

```python
# Version 1 routes
v1 = Router(prefix=\"/v1\")

@v1.get(\"/users\")
async def list_users_v1():
    # Original implementation
    return await User.all()

# Version 2 routes with enhanced functionality
v2 = Router(prefix=\"/v2\")

@v2.get(\"/users\")
async def list_users_v2(page: int = 1, limit: int = 20):
    # Enhanced with pagination
    users = await User.all().limit(limit).offset((page - 1) * limit)
    return {
        \"data\": [u.to_dict() for u in users],
        \"page\": page,
        \"limit\": limit
    }

# Register both versions
app.include_router(v1)
app.include_router(v2)
```

## Pagination

```python
@app.get(\"/posts\")
async def list_posts(page: int = 1, limit: int = 10):
    \"\"\"Offset-based pagination.\"\"\"
    total = await Post.count()
    posts = await Post.all().limit(limit).offset((page - 1) * limit)
    
    return {
        \"data\": [p.to_dict() for p in posts],
        \"pagination\": {
            \"page\": page,
            \"limit\": limit,
            \"total\": total,
            \"pages\": (total + limit - 1) // limit
        }
    }
```

## Error Handling

```python
from eden.exceptions import ValidationError, PermissionDenied

@app.errorhandler(ValidationError)
async def handle_validation_error(request, error):
    return JSONResponse({
        \"error\": \"Validation failed\",
        \"details\": error.messages
    }, status_code=400)

@app.errorhandler(PermissionDenied)
async def handle_permission_denied(request, error):
    return JSONResponse({
        \"error\": \"Permission denied\",
        \"message\": str(error)
    }, status_code=403)
```
