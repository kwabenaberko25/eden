# Phase 8: Real-World Patterns

This phase covers production-ready patterns, optimization, and deployment strategies.

---

## What You'll Learn

- Production configuration
- Middleware stack design
- Error handling best practices
- Caching strategies
- Background tasks
- Testing strategies
- Deployment

---

## 8.1 Production Configuration

**Advanced** - Production app setup:

```python
from eden import Eden

app = Eden\(
    title="Production App",
    debug=False,  # Never True in production!
    secret_key="secure-random-key-from-env"
)

# Add production middleware
app.add_middleware("security")
app.add_middleware("cors", allow_origins=["https://yourdomain.com"])
app.add_middleware("gzip", minimum_size=500)
app.add_middleware("ratelimit", max_requests=100, window_seconds=60)
```

---

## 8.2 Error Handling

**Advanced** - Global error handler:

```python
from starlette.exceptions import HTTPException

@app.exception_handler(HTTPException)
async def handle_http_exception(request, exc):
    return app.render(f"errors/{exc.status_code}.html", {
        "request": request,
        "error": exc
    })

@app.exception_handler(Exception)
async def handle_exception(request, exc):
    # Log the error
    import logging
    logging.exception("Unhandled exception")
    
    return app.render("errors/500.html", {
        "request": request
    }, status_code=500)
```

---

## 8.3 Caching

**Intermediate** - Page caching:

```python
app.add_middleware("cache", ttl=300)  # Cache for 5 minutes
```

**Intermediate** - Programmatic cache:

```python
from eden.cache import TenantCacheWrapper, InMemoryCache

cache = TenantCacheWrapper(backend=InMemoryCache())

@router.get("/stats")
async def stats(request):
    data = await cache.get("stats")
    if data:
        return {"source": "cache", "data": data}
    
    data = await calculate_stats()
    await cache.set("stats", data, ttl=60)
    return {"source": "db", "data": data}
```

---

## 8.4 Background Tasks

**Advanced** - Define tasks:

```python
from eden import Eden
from taskiq import InMemoryBroker

app = Eden\()

@app.task
async def send_welcome_email(user_id: int):
    user = await User.get(user_id)
    # Send email...
    pass

@app.task
async def process_upload(file_id: int):
    # Process file...
    pass
```

**Advanced** - Schedule tasks:

```python
# Run after delay
await app.task.schedule(send_welcome_email, delay=60, user_id=user.id)

# Run immediately
await app.task.defer(send_welcome_email, user_id=user.id)
```

---

## 8.5 Logging

**Advanced** - Configure logging:

```python
from eden.logging import setup_logging, get_logger

setup_logging(level="INFO", json_format=True)

logger = get_logger(__name__)

@router.get("/")
async def index(request):
    logger.info("Index page accessed")
    return {"message": "Hello"}
```

---

## 8.6 Testing

**Intermediate** - Test client:

```python
import pytest
from eden import Eden

@pytest.fixture
def app():
    test_app = Eden\(title="Test App")
    return test_app

@pytest.fixture
def client(app):
    from starlette.testclient import TestClient
    return TestClient(app)

def test_index(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello"}
```

---

## 8.7 File Storage

**Intermediate** - Local storage:

```python
from eden import storage, LocalStorageBackend

storage.register("local", LocalStorageBackend(base_path="media"))

@router.post("/upload")
async def upload(request):
    file = await request.form()
    uploaded = file.get("file")
    
    path = await storage.save(uploaded)
    url = storage.url(path)
    
    return {"url": url}
```

---

## 8.8 Email

**Intermediate** - Send email:

```python
from eden import send_mail

await send_mail(
    to="user@example.com",
    subject="Welcome",
    body="Welcome to our platform!"
)
```

---

## 8.9 Deployment

### Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--workers", "4"]
```

### Production Server

```bash
# Run with multiple workers
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4
```

### Environment Variables

```bash
export EDEN_DEBUG=False
export EDEN_SECRET_KEY=your-secret-key
export DATABASE_URL=postgresql://user:pass@localhost/db
export REDIS_URL=redis://localhost:6379
```

---

## 8.10 Complete Production Example

```python
# app.py
from eden import Eden
from eden.logging import setup_logging

# Configure logging
setup_logging(level="INFO", json_format=False)

app = Eden\(
    title="Production Blog",
    debug=False,
    secret_key="CHANGE-THIS-IN-PRODUCTION"
)

# Middleware stack (order matters!)
app.add_middleware("security")           # 1. Security headers
app.add_middleware("cors", allow_origins=["https://myblog.com"])
app.add_middleware("gzip", minimum_size=500)  # 2. Compression
app.add_middleware("ratelimit", max_requests=100, window_seconds=60)
app.add_middleware("session", secret_key="CHANGE-THIS")
app.add_middleware("telemetry")          # 3. Performance monitoring

# Routes
from routes import api_router
app.include_router(api_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

---

## Summary

You learned:
- Production configuration
- Error handling best practices
- Caching strategies
- Background tasks
- Logging
- Testing
- File storage
- Email
- Deployment with Docker
- Environment configuration

---

## Congratulations!

You've completed the Eden Framework tutorial! 

You now have a comprehensive understanding of:
- Building web applications with Eden
- Database modeling and queries
- Routing and request handling
- Forms and validation
- Authentication and authorization
- Permissions
- Templating
- Production patterns

**Keep building with Eden!**

