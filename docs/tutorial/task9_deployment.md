# Task 9: Deploy Application

**Goal**: Seamlessly transition from local development to a production-ready environment using **Docker** and secure configuration patterns.

---

## 🐋 Step 9.1: Containerizing with Docker

Eden projects come with a production-optimized `Dockerfile` out of the box. This ensures your app runs identically across development, staging, and production.

**File**: `Dockerfile`

```dockerfile
# 🏗️ Build Stage
FROM python:3.11-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# 🚀 Runtime Stage
FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /install /usr/local
COPY . .

# Security: Run as non-privileged user
RUN adduser --disabled-password --no-create-home eden
USER eden

# Launch the app using the 'eden' runner
CMD ["eden", "run", "--host", "0.0.0.0", "--no-reload"]
```

### 🛰️ Building the Image

```bash
docker build -t my-eden-app .
```

---

## ⚙️ Step 9.2: Production Settings

In production, you must use environment variables to override sensitive defaults.

**Create a `.env` file (not committed to Git)**:
```env
EDEN_DEBUG=false
EDEN_SECRET_KEY=9a2b3c4d5e6f7g8h9i0j...
DATABASE_URL=postgresql+asyncpg://user:pass@dbserver:5432/myapp
LOG_LEVEL=INFO
```

> [!IMPORTANT]
> Never commit your `.env` file to version control. Use secret management services (like AWS Secrets Manager or GitHub Secrets) for production deployments.

---

## ⚡ Step 9.3: High-Performance Runner (Gunicorn)

While `eden run` is great for development, for high-traffic production use the **Gunicorn** server with asynchronous workers.

```bash
gunicorn app:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### 🧠 Breakdown:
- `-w 4`: Runs 4 independent worker processes (usually `2 * CPU cores + 1`).
- `-k uvicorn...`: Tells Gunicorn to use the high-performance Uvicorn worker for async ASGI.

---

### **Next Task**: [Testing & Automation](./task10_testing.md)
