# Deployment & Observability 🚀

Taking your Eden application from development to production requires attention to performance, security, and monitoring.

## Local Development

Run your Eden application locally during development:

```bash
eden run
```

This starts the development server with auto-reload enabled.

---

## Production Configuration

Always use environment variables for sensitive configuration.

```text
EDEN_DEBUG=False
DATABASE_URL=postgresql+asyncpg://user:pass@db:5432/eden
REDIS_URL=redis://queue:6379/0
SECRET_KEY=y0ur-5ecr3t-k3y-h3r3
```

---

## Scaling with Uvicorn

In production, run your Eden application using Gunicorn with Uvicorn workers for optimized performance.

```bash
gunicorn app:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

---

## Docker Deployment 🐳

Eden is designed to be container-first. Here is a standard `Dockerfile` for an Eden project:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Copy application files
COPY . .

# Run as non-root user
RUN useradd -m edenuser
USER edenuser

CMD ["gunicorn", "app:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]
```

---

## Observability 🛰️

Eden includes native telemetry hooks that can be integrated with tools like **Prometheus** and **OpenTelemetry**.

### Logging
Configure structured logging for better searchability in production.

```python
import logging
from eden.logging import JSONFormatter

handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logging.getLogger("eden").addHandler(handler)
```

### Error Tracking (Sentry) 🏹
Eden integrates seamlessly with Sentry for real-time error tracking.

```python
import sentry_sdk
from sentry_sdk.integrations.starlette import StarletteIntegration

sentry_sdk.init(
    dsn="your-dsn-here",
    integrations=[StarletteIntegration(app=app)]
)
```

### Health Probes
Expose standard health check endpoints for Kubernetes liveness and readiness probes.

```python
# Available at /health/ by default
```

---

## Security Checklist 🛡️

Before going live, ensure:
1. `EDEN_DEBUG` is set to `False`.
2. `SECRET_KEY` is a long, random string.
3. `csrf` and `security` middlewares are enabled.
4. Database connections are pooled correctly.
5. All traffic is served over HTTPS.

---

**Congratulations!** You have mastered the Eden Framework documentation.
