# Deployment & Operations 🚀

Taking your Eden application from development to production requires attention to performance, security, and scalability. This guide covers the end-to-end production workflow.

---

## Production Runtime (Gunicorn + Uvicorn)

In development, `eden start` is sufficient. In production, you must use a process manager like **Gunicorn** with **Uvicorn workers** to handle concurrent loads and automatic process recycling.

```bash
# Example: 4 workers (typically 2 x num_cores + 1)
gunicorn app:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

---

## Nginx Reverse Proxy 🛠️

Always put a reverse proxy like Nginx in front of your Python application. It handles SSL termination, static file serving, and buffers slow clients.

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location /static/ {
        alias /app/static/;
        expires 30d;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## Environment Management

Eden uses `.env` files for local development, but in production, you should use system environment variables or a secret manager (Secrets Manager, Vault).

### Required Variables
- `EDEN_DEBUG=False`
- `DATABASE_URL=postgresql+asyncpg://user:pass@db:5432/eden`
- `SECRET_KEY`: A cryptographically secure random string.
- `ALLOWED_HOSTS`: Comma-separated list of domains.

---

## Zero-Downtime Migrations 🔄

When deploying new code that involves database changes:
1. **Pre-deploy**: Apply "additive" migrations (new tables/columns) that don't break old code.
2. **Deploy**: Roll out the new application code.
3. **Post-deploy**: Clean up old columns or data if necessary.

```bash
# Apply pending migrations before restarting the app
eden migrate upgrade head
```

---

## Health & Monitoring

Eden exposes a built-in health check endpoint that verifies database and cache connectivity.

- **Endpoint**: `GET /health`
- **Response**:
  ```json
  {
    "status": "healthy",
    "db": "connected",
    "cache": "connected",
    "uptime": "5d 12h"
  }
  ```

### Sentry Integration
```python
import sentry_sdk
from eden.extras import sentry

sentry.init(dsn="your-sentry-dsn")
```

---

## Security Hardening Checklist

- [ ] Disable `DEBUG` mode.
- [ ] Set `SESSION_COOKIE_SECURE=True`.
- [ ] Use `Strict-Transport-Security` (HSTS) headers.
- [ ] Ensure `ALLOWED_HOSTS` is strictly defined.
- [ ] Run your Docker container as a non-root user.

---

**Next Steps**: [Troubleshooting Guide](troubleshooting.md)
