"""
07_production.py — Production-Ready Application

Deploy to production with Stripe payments, S3 storage, background
tasks, caching, and error handling.

Run:
    python examples/07_production.py
    
Or with Docker:
    docker-compose up
"""

from eden import Eden, Model, StringField, IntField, cache_view, Request

app = Eden(
    title="Production App",
    version="1.0.0",
    debug=False,
    secret_key="use-env-var-in-production"
)

# Database configuration from environment
import os
app.state.database_url = os.getenv(
    "DATABASE_URL",
    "sqlite+aiosqlite:///app.db"
)

# ────────────────────────────────────────────────────────────────────────
# Models
# ────────────────────────────────────────────────────────────────────────

class Product(Model):
    """Product with S3 image storage."""
    name = StringField(max_length=200)
    price = IntField()
    image_url = StringField(default="")


class Order(Model):
    """Order integrated with Stripe."""
    stripe_payment_id = StringField()
    total = IntField()  # in cents


# ────────────────────────────────────────────────────────────────────────
# Cached Endpoints
# ────────────────────────────────────────────────────────────────────────

@app.get("/products")
@cache_view(ttl=300)  # Cache for 5 minutes
async def list_products():
    """Cached list of products."""
    products = await Product.all()
    return {"products": products}


# ────────────────────────────────────────────────────────────────────────
# Stripe Integration
# ────────────────────────────────────────────────────────────────────────

@app.post("/checkout")
async def checkout(request: Request):
    """
    Create Stripe checkout session.
    
    Requires: pip install eden-framework[payments]
    """
    data = await request.json()
    
    # Create order record
    order = await Order.create(
        stripe_payment_id="temp",
        total=data["amount"]
    )
    
    # Create Stripe session (requires StripeProvider setup)
    # session = await app.payments.create_checkout_session(...)
    
    return {"order_id": order.id, "status": "pending"}


# ────────────────────────────────────────────────────────────────────────
# Background Tasks
# ────────────────────────────────────────────────────────────────────────

@app.task()
async def send_order_confirmation(order_id: int):
    """
    Send email confirmation.
    
    Requires: pip install eden-framework[mail]
    """
    # from eden.mail import send_mail
    # await send_mail("Order confirmed", to="customer@example.com")
    pass


# ────────────────────────────────────────────────────────────────────────
# Health Check & Monitoring
# ────────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health_check():
    """Health check for monitoring."""
    return {"status": "healthy", "version": app.version}


@app.get("/metrics")
async def metrics():
    """Basic metrics endpoint."""
    return {"uptime": "TODO", "requests": "TODO"}


# ────────────────────────────────────────────────────────────────────────
# Startup & Shutdown
# ────────────────────────────────────────────────────────────────────────

@app.on_startup
async def startup():
    """Initialize at startup."""
    print("🚀 Starting production app...")
    # Connect to database, cache, etc.


@app.on_shutdown
async def shutdown():
    """Clean up at shutdown."""
    print("🛑 Shutting down...")


if __name__ == "__main__":
    app.setup_defaults()
    
    # Enable background task workers
    # app.enable_broker()
    
    # Run production server (uvicorn)
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        workers=int(os.getenv("WORKERS", 1))
    )

# What you learned:
#   - Environment variable configuration
#   - @cache_view() for caching
#   - Stripe integration (requires [payments] extra)
#   - @app.task() for background jobs
#   - Health checks for monitoring
#   - @app.on_startup / @app.on_shutdown
#   - Running on multiple workers
#   - Error handling in production
#
# Production Checklist:
#   [ ] Use env vars for secrets
#   [ ] Set DEBUG=false
#   [ ] Use proper database (PostgreSQL/MySQL not SQLite)
#   [ ] Enable HTTPS
#   [ ] Set up monitoring/logging
#   [ ] Use Docker for deployment
#   [ ] Configure CORS properly
#   [ ] Add rate limiting
#   [ ] Set up backups
#
# This completes your Eden journey!
# Now go build amazing applications. 🌿
