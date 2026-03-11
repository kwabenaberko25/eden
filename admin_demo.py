import asyncio
import os
from datetime import datetime, timedelta
import uuid

from sqlalchemy import select
from eden import (
    Eden, 
    Tenant, 
    TenantMixin, 
    EdenModel,
    StringField,
    DateTimeField,
    FloatField,
    Relationship
)
from eden.orm import init_db
from eden.admin import admin, ModelAdmin

# Initialize DB globally
db = init_db("sqlite+aiosqlite:///admin_demo.sqlite", echo=False)

# 1. Initialize Eden App
app = Eden(
    title="Eden Premium Admin",
    debug=True,
)

# Mock Auth Middleware for Demo purposes
class MockAuthMiddleware:
    def __init__(self, app):
        self.app = app
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # Inject a mock staff user into the request state
            scope["state"] = scope.get("state", {})
            # We use a simple object that satisfies the is_staff/is_superuser check
            class MockUser:
                is_staff = True
                is_superuser = True
                id = 1
                full_name = "Admin Demo User"
            
            # Starlette's Request state is stored in scope["state"]
            # but we can also set it directly if we use our own request wrapper.
            # However, the easiest way for Starlette middleware is to use the scope.
            # But Starlette's Request object initialization does: self.state = State(scope.get("state", {}))
            # So we can just set it here.
            from starlette.datastructures import State
            if "state" not in scope:
                scope["state"] = {}
            scope["state"]["user"] = MockUser()
            
        await self.app(scope, receive, send)

app.add_middleware(MockAuthMiddleware)
app.db = db

@app.on_startup
async def startup():
    await db.connect(create_tables=True)

@app.on_shutdown
async def shutdown():
    await db.disconnect()


# 2. Define Sophisticated Data Models
# Rename to Demo* to avoid clashing with internal Eden models like 'User'

class DemoUser(EdenModel, TenantMixin):
    """Users belonging to a Tenant (Organization)."""
    __tablename__ = "demo_users"
    email = StringField(unique=True, index=True)
    full_name = StringField()
    role = StringField(default="member")  # admin, editor, member
    last_login = DateTimeField(nullable=True)
    # tenant_id is added by TenantMixin
    organization = Relationship(lambda: Tenant, foreign_keys="DemoUser.tenant_id")


class DemoProject(EdenModel, TenantMixin):
    """Projects created by users within an Organization."""
    __tablename__ = "demo_projects"
    title = StringField()
    description = StringField(nullable=True)
    status = StringField(default="active")  # active, archived, completed
    created_at = DateTimeField(default=datetime.utcnow)
    organization = Relationship(lambda: Tenant, foreign_keys="DemoProject.tenant_id")

class DemoTransaction(EdenModel, TenantMixin):
    """Financial transactions for reports."""
    __tablename__ = "demo_transactions"
    amount = FloatField()
    currency = StringField(default="USD")
    status = StringField(default="pending")  # pending, completed, failed
    created_at = DateTimeField(default=datetime.utcnow)
    organization = Relationship(lambda: Tenant, foreign_keys="DemoTransaction.tenant_id")


# 3. Custom Admin Configuration
class TenantAdmin(ModelAdmin):
    list_display = ["name", "slug", "plan", "is_active"]
    search_fields = ["name", "slug"]
    list_filter = ["plan", "is_active"]

# Unregister if previously registered (stability)
try:
    admin.unregister(Tenant)
except:
    pass
admin.register(Tenant, TenantAdmin)

class UserAdmin(ModelAdmin):
    list_display = ["full_name", "email", "role", "tenant_id"]
    search_fields = ["email", "full_name"]
    list_filter = ["role"]
    
    def get_list_actions(self, obj):
        return [
            {"label": "Deactivate" if obj.role != "inactive" else "Activate", "url": f"/admin/user/{obj.id}/toggle"}
        ]

admin.register(DemoUser, UserAdmin)

class TransactionAdmin(ModelAdmin):
    list_display = ["amount", "currency", "status", "created_at"]
    list_filter = ["status", "currency"]
    
    def get_list_header_stats(self, model):
        """Example of inline stats at the top of the list view."""
        return [
            {"label": "Total Revenue", "value": "$12,450.00", "trend": "+12%", "is_positive": True},
            {"label": "Pending", "value": "14", "trend": "-2", "is_positive": False},
        ]

admin.register(DemoTransaction, TransactionAdmin)

# 4. Global Search / Command Palette Hook
@app.route("/admin/search")
async def admin_search(request):
    query = request.query_params.get("q", "")
    return {"results": [{"title": f"Result for {query}", "url": "#"}]}

# 5. Seed Data for Impact
async def seed_data():
    # Ensure tables exist
    await db.connect(create_tables=True)
    
    async with db.session() as session:
        # Check if we already have data
        existing = await session.execute(select(Tenant))
        if existing.first():
            print("Skipping seed: Data already exists.")
            await db.disconnect()
            return

        # Create Tenants
        acme = Tenant(name="Acme Corp", slug="acme", plan="enterprise")
        stark = Tenant(name="Stark Industries", slug="stark", plan="pro")
        session.add_all([acme, stark])
        await session.commit()

        # Create Users
        users = [
            DemoUser(full_name="Tony Stark", email="tony@stark.com", role="admin", tenant_id=stark.id),
            DemoUser(full_name="Pepper Potts", email="pepper@stark.com", role="admin", tenant_id=stark.id),
            DemoUser(full_name="Peter Parker", email="peter@dailybugle.com", role="member", tenant_id=stark.id),
            DemoUser(full_name="Cobby Admin", email="cobby@acme.com", role="admin", tenant_id=acme.id),
        ]
        session.add_all(users)
        
        # Create Transactions
        for i in range(10):
            tid = stark.id if i % 3 == 0 else acme.id
            session.add(DemoTransaction(
                amount=float(100 * (i + 1)), 
                status="completed" if i % 2 == 0 else "pending",
                tenant_id=tid
            ))
        
        await session.commit()
    
    await db.disconnect()
    print("✅ Demo data seeded successfully.")

# 6. Run the App
if __name__ == "__main__":
    import sys
    
    # Simple CLI to seed or run
    if "seed" in sys.argv:
        asyncio.run(seed_data())
    else:
        app.mount_admin()
        app.run(reload=False)
