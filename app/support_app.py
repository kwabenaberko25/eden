import sys
import os
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from eden import Eden, Route, admin_site
from eden.admin.models import SupportTicket, TicketMessage
from eden.auth.models import User
from eden.db import init_db
from eden.htmx import HtmxResponse, is_htmx
from eden.websocket import WebSocketRouter, connection_manager
from eden.payments import StripeProvider
from eden.tenancy import TenantMixin
import asyncio
import json

# ============================================================================
# 1. APP INITIALIZATION
# ============================================================================
app = Eden(debug=True)
db = init_db("sqlite+aiosqlite:///eden.db", app=app)

# ============================================================================
# 2. TENANCY SETUP (Multi-Tenant)
# ============================================================================
# Enable multi-tenancy with subdomain strategy (or use "header" for X-Tenant-ID)
app.add_middleware(
    "tenant",
    strategy="header",  # Use header strategy for easier testing: X-Tenant-ID: demo
    enforce=False,      # Allow requests without tenant (for public endpoints)
    exempt_paths=["/health", "/ready", "/static", "/api/auth"]
)

# ============================================================================
# 3. BACKGROUND TASKS SETUP (Redis with InMemory fallback)
# ============================================================================
app.setup_tasks()

@app.task()
async def send_support_email(ticket_id: str, message: str):
    """Background task to send support ticket notifications"""
    await asyncio.sleep(1)  # Simulate email sending
    print(f"[TASK] Support email sent for ticket {ticket_id}: {message}")

@app.schedule("0 * * * *")  # Every hour
async def cleanup_old_messages():
    """Periodic task to clean up old messages"""
    print("[SCHEDULED] Cleanup task executed")

# ============================================================================
# 4. STRIPE SETUP (Payment Processing)
# ============================================================================
# Configure Stripe (optional - uses dummy keys for demo)
stripe_provider = StripeProvider(
    api_key=os.getenv("STRIPE_API_KEY", "sk_test_demo"),
    webhook_secret=os.getenv("STRIPE_WEBHOOK_SECRET", "whsec_demo"),
)
app.configure_payments(stripe_provider)

# ============================================================================
# 5. WEBSOCKETS SETUP (Real-time Communication)
# ============================================================================
ws = WebSocketRouter(prefix="/ws", auth_required=False)

@ws.on_connect
async def on_ws_connect(socket, manager):
    """Handle WebSocket connection"""
    await manager.broadcast({
        "type": "notification",
        "message": "User connected to chat",
    }, channel="chat")
    print("[WS] User connected")

@ws.on_disconnect
async def on_ws_disconnect(socket, manager):
    """Handle WebSocket disconnection"""
    await manager.broadcast({
        "type": "notification",
        "message": "User disconnected from chat",
    }, channel="chat")
    print("[WS] User disconnected")

@ws.on("message")
async def on_ws_message(socket, data, manager):
    """Handle WebSocket messages"""
    text = data.get("text", "")
    await manager.broadcast({
        "type": "message",
        "text": text,
        "timestamp": str(__import__("datetime").datetime.now()),
    }, channel="chat", exclude=socket)  # Exclude sender for client-side echo
    print(f"[WS] Message: {text}")

@ws.on("notification")
async def on_ws_notification(socket, data, manager):
    """Handle typed notifications"""
    await manager.broadcast(
        {"type": "notification", "message": data.get("message", "")},
        channel="chat"
    )

app.routes.extend(ws.routes)

# Register admin
app.include_router(admin_site.build_router())


# ============================================================================
# FEATURE DEMONSTRATION ROUTES
# ============================================================================

# --- 1. HTMX INTEGRATION ---
@app.get("/demo/htmx")
async def htmx_demo(request):
    """HTMX feature demo page"""
    return await app.render("demo_htmx.html", {"request": request})

@app.get("/api/items")
async def list_items(request):
    """API endpoint for HTMX fragment rendering"""
    items = [
        {"id": "1", "name": "Item 1", "status": "active"},
        {"id": "2", "name": "Item 2", "status": "pending"},
        {"id": "3", "name": "Item 3", "status": "completed"},
    ]
    
    if is_htmx(request):
        # Return fragment for HTMX swap
        html = f"""
        <div id="items-list">
            {''.join(f'<div class="item"><strong>{item["name"]}</strong> - {item["status"]}</div>' for item in items)}
        </div>
        """
        return HtmxResponse(html).trigger("itemsLoaded", {"count": len(items)})
    
    # Full page response for normal requests
    from starlette.responses import JSONResponse
    return JSONResponse({"items": items})

@app.post("/api/items/add")
async def add_item(request):
    """Add item endpoint (HTMX friendly)"""
    data = await request.json()
    new_item = f"""<div class="item"><strong>{data.get('name', 'New Item')}</strong> - new</div>"""
    
    if is_htmx(request):
        return HtmxResponse(new_item).trigger("itemAdded")
    
    return {"status": "success"}

# --- 2. WEBSOCKETS DEMO ---
@app.get("/demo/websockets")
async def websockets_demo(request):
    """WebSocket feature demo page"""
    return await app.render("demo_websockets.html", {"request": request})

@app.get("/api/ws-status")
async def ws_status(request):
    """Get WebSocket connection status"""
    from starlette.responses import JSONResponse
    
    active_conns = len(connection_manager._connections)
    
    return JSONResponse({
        "websocket_enabled": True,
        "active_connections": active_conns,
        "ws_url": "ws://localhost:8001/ws",
        "features": [
            "Pub/sub broadcasting",
            "Heartbeat monitoring",
            "User isolation",
            "CSRF protection",
        ]
    })

# --- 3. BACKGROUND TASKS DEMO ---
@app.get("/demo/tasks")
async def tasks_demo(request):
    """Background tasks feature demo page"""
    return await app.render("demo_tasks.html", {"request": request})

@app.post("/api/send-email")
async def queue_email(request):
    """Queue a background email task"""
    data = await request.json()
    ticket_id = data.get("ticket_id", "demo-ticket")
    message = data.get("message", "Support ticket received")
    
    # Enqueue background task
    task_id = await send_support_email.kiq(ticket_id, message)
    
    from starlette.responses import JSONResponse
    return JSONResponse({
        "status": "queued",
        "task_id": str(task_id),
        "message": f"Email task queued for ticket {ticket_id}"
    })

@app.get("/api/task-status/{task_id}")
async def get_task_status(request, task_id: str):
    """Get background task status"""
    from starlette.responses import JSONResponse
    
    result = await app.broker.task_result_backend.get_result(task_id)
    
    if result:
        return JSONResponse({
            "task_id": task_id,
            "status": result.status,  # pending, running, success, failed
            "progress": result.progress,
            "result": result.result,
            "error": result.error,
        })
    
    return JSONResponse({"error": "Task not found"}, status_code=404)

# --- 4. STRIPE INTEGRATION DEMO ---
@app.get("/demo/stripe")
async def stripe_demo(request):
    """Stripe payment feature demo page"""
    return await app.render("demo_stripe.html", {"request": request})

@app.post("/api/checkout")
async def create_checkout(request):
    """Create Stripe checkout session"""
    from starlette.responses import JSONResponse
    
    data = await request.json()
    plan = data.get("plan", "basic")  # basic, pro, enterprise
    
    # In production, use actual Stripe prices
    prices = {
        "basic": "price_basic_demo",
        "pro": "price_pro_demo",
        "enterprise": "price_enterprise_demo",
    }
    
    try:
        # This would call Stripe in production
        # For demo, return mock response
        checkout_url = f"https://stripe-demo.example.com/checkout/{plan}"
        
        return JSONResponse({
            "status": "success",
            "checkout_url": checkout_url,
            "plan": plan,
            "message": f"Checkout session created for {plan} plan (DEMO)"
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)

@app.post("/api/billing-portal")
async def create_billing_portal(request):
    """Create Stripe billing portal"""
    from starlette.responses import JSONResponse
    
    try:
        # This would call Stripe in production
        portal_url = "https://stripe-demo.example.com/billing"
        
        return JSONResponse({
            "status": "success",
            "portal_url": portal_url,
            "message": "Billing portal opened (DEMO)"
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)

# --- 5. TENANCY (MULTI-TENANT) DEMO ---
@app.get("/demo/tenancy")
async def tenancy_demo(request):
    """Multi-tenant feature demo page"""
    tenant = getattr(request, "tenant", None)
    tenant_id = tenant.id if tenant else "none"
    
    return await app.render("demo_tenancy.html", {
        "request": request,
        "current_tenant": tenant_id,
        "tenant_info": {
            "id": tenant_id,
            "name": f"Tenant {tenant_id}" if tenant else "Public/No Tenant",
        }
    })

@app.get("/api/tenant-info")
async def get_tenant_info(request):
    """Get current tenant information"""
    from starlette.responses import JSONResponse
    
    tenant = getattr(request, "tenant", None)
    
    return JSONResponse({
        "current_tenant": str(tenant.id) if tenant else None,
        "tenant_name": f"Tenant {tenant.id}" if tenant else "No Tenant",
        "features": [
            "Multi-schema support",
            "Automatic query filtering",
            "Fail-secure enforcement",
            "4 resolution strategies (subdomain, header, session, path)",
        ]
    })

# ============================================================================
# FEATURE SHOWCASE ROUTES
# ============================================================================

@app.get("/")
async def home(request):
    """Main demo page with all features"""
    return await app.render("demo_home.html", {"request": request})

@app.get("/api/subscription-status")
async def subscription_status(request):
    """Get subscription status"""
    from starlette.responses import JSONResponse
    
    # In production, check actual subscription
    return JSONResponse({
        "is_subscribed": False,
        "plan": None,
        "message": "No active subscription (DEMO)"
    })

@app.get("/demo")
async def demo_index(request):
    """Demo features index page"""
    features = [
        {
            "name": "HTMX Integration",
            "url": "/demo/htmx",
            "description": "Smart fragment rendering with HX-* headers"
        },
        {
            "name": "WebSockets",
            "url": "/demo/websockets",
            "description": "Real-time bidirectional communication"
        },
        {
            "name": "Background Tasks",
            "url": "/demo/tasks",
            "description": "Async task queue with Redis (or InMemory fallback)"
        },
        {
            "name": "Stripe Integration",
            "url": "/demo/stripe",
            "description": "Payment processing and subscriptions"
        },
        {
            "name": "Multi-Tenant",
            "url": "/demo/tenancy",
            "description": "Tenant isolation and multi-schema support"
        },
    ]
    
    return await app.render("demo_features.html", {
        "request": request,
        "features": features
    })

@app.get("/support", methods=["GET"])
async def support_demo(request):
    """Original support demo"""
    return await app.render("support_demo.html", {"request": request})

    # Canonical way to initialize schema in Eden
    await db.connect(create_tables=True)
    
    import uuid
    DEMO_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
    
    # Create a demo user if it doesn't exist
    async with db.session() as session:
        user = await session.get(User, DEMO_USER_ID)
        if not user:
            user = User(
                id=DEMO_USER_ID,
                username="demo_user",
                email="demo@eden-framework.dev",
                is_superuser=True,
                password_hash="demo_password" # In real app use set_password
            )
            session.add(user)
            await session.commit()
            print(f"Demo user created with ID: {DEMO_USER_ID}")

if __name__ == "__main__":
    import uvicorn
    
    # Run setup
    asyncio.run(setup_db())
    
    uvicorn.run(app, host="127.0.0.1", port=8001)
