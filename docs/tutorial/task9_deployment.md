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

## 🌍 Step 9.4: Deploying to Production

### Option A: Traditional Cloud (AWS EC2, DigitalOcean, Linode)

1. **Create a server** running Ubuntu 22.04 LTS
2. **Install Docker**:
   ```bash
   curl -fsSL https://get.docker.com -o get-docker.sh
   sudo sh get-docker.sh
   ```

3. **Push your image**:
   ```bash
   docker login
   docker tag my-eden-app your-registry/my-eden-app:latest
   docker push your-registry/my-eden-app:latest
   ```

4. **Run the container**:
   ```bash
   docker run -d \
     -e DATABASE_URL="postgresql://..." \
     -e EDEN_SECRET_KEY="..." \
     -p 8000:8000 \
     your-registry/my-eden-app:latest
   ```

### Option B: Serverless (AWS Lambda, Google Cloud Run)

Eden can run serverlessly with minimal changes:

```python
# app.py - Same Eden app code
from mangum import Mangum

app = create_app()

# Wrap for serverless
handler = Mangum(app)
```

Deploy to AWS Lambda:
```bash
sam build
sam deploy
```

### Option C: Containerized Orchestration (Kubernetes)

For scale, use Kubernetes:

```yaml
# kubernetes.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: eden-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: eden-app
  template:
    metadata:
      labels:
        app: eden-app
    spec:
      containers:
      - name: eden-app
        image: your-registry/my-eden-app:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: eden-secrets
              key: database-url
---
apiVersion: v1
kind: Service
metadata:
  name: eden-app
spec:
  selector:
    app: eden-app
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
```

Deploy:
```bash
kubectl apply -f kubernetes.yaml
```

---

## 🔒 Step 9.5: SSL/TLS & HTTPS

Always use HTTPS in production. Use a reverse proxy like **Nginx**:

```nginx
# /etc/nginx/sites-available/eden-app
server {
    listen 80;
    server_name example.com;
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name example.com;
    
    # SSL certificates (from Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000" always;
    
    # Route to Eden app
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable SSL with Let's Encrypt:
```bash
sudo certbot certonly --nginx -d example.com
```

---

## 📊 Step 9.6: Monitoring & Error Tracking

Set up application monitoring to catch issues in production:

```python
# app/__init__.py
from eden.telemetry import setup_sentry

# Configure error tracking
setup_sentry(
    dsn="https://your-sentry-dsn@sentry.io/...",
    environment="production",
    traces_sample_rate=0.1  # Sample 10% of transactions
)

def create_app():
    app = Eden(...)
    
    # Enable structured logging
    app.enable_logging(
        level="INFO",
        format="json"  # Structured JSON for log aggregation
    )
    
    return app
```

Monitor with tools like:
- **Sentry**: Application error tracking
- **Datadog**: Infrastructure & performance monitoring
- **ELK Stack**: Log aggregation and analysis
- **Prometheus + Grafana**: Metrics and dashboards

---

## ✅ Step 9.7: Deployment Checklist

Before going live:

```markdown
## Pre-Production Checklist

- [ ] All debugging disabled (`EDEN_DEBUG=false`)
- [ ] Database migrations applied and tested
- [ ] SSL/TLS certificates installed
- [ ] Environment variables configured
- [ ] Backup strategy implemented
- [ ] Rate limiting configured
- [ ] CDN set up for static assets (if needed)
- [ ] DNS and load balancing configured
- [ ] Security headers enabled (CSP, HSTS, X-Frame-Options)
- [ ] Database backups automated
- [ ] Monitoring and alerting configured
- [ ] Error tracking (Sentry) enabled
- [ ] Log aggregation set up
- [ ] HTTPS redirect in place
- [ ] Tests passing locally
```

---

### **Next Task**: [Testing & Automation](./task10_testing.md)
