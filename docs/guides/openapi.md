# OpenAPI & Swagger Documentation 📚

Eden automatically generates interactive API documentation from your routes. This guide covers OpenAPI schemas and Swagger UI.

## Automatic Documentation

Eden exposes your API documentation at:

- **Swagger UI**: `/docs`
- **ReDoc**: `/redoc`
- **OpenAPI Schema**: `/openapi.json`

## Configuring OpenAPI

```python
from eden import Eden

app = Eden(
    title="My API",
    version="1.0.0",
    description="A description of your API",
    contact={
        "name": "API Support",
        "url": "https://example.com/support",
        "email": "support@example.com"
    },
    license_info={
        "name": "Apache 2.0",
        "url": "https://www.apache.org/licenses/LICENSE-2.0.html"
    }
)
```

## Route Documentation

```python
from eden import Eden
from unittest.mock import MagicMock

app = Eden()
User = MagicMock()

@app.get("/users/{user_id}", 
    summary="Get a specific user",
    description="Retrieve detailed information about a user",
    tags=["users"],
    responses={
        200: {"description": "User found"},
        404: {"description": "User not found"}
    }
)
async def get_user(user_id: int):
    """Get user by ID."""
    user = await User.get(user_id)
    if not user:
        return {"error": "Not found"}, 404
    return user.to_dict()
```

## Schema Documentation

Eden automatically documents request/response schemas:

```python
from eden import Eden
from pydantic import BaseModel
from unittest.mock import MagicMock

app = Eden()
User = MagicMock()

class UserCreate(BaseModel):
    name: str
    email: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "John Doe",
                "email": "john@example.com"
            }
        }

@app.post("/users", response_model=dict)
async def create_user(data: UserCreate):
    """Create a new user."""
    user = await User.create(**data.dict())
    return user.to_dict()
```

## Best Practices

- ✅ Add `summary` and `description` to important endpoints
- ✅ Document all possible status codes with `responses`
- ✅ Use `tags` to group related endpoints
- ✅ Provide example data in schema definitions
- ✅ Set `include_in_schema=False` for internal endpoints
