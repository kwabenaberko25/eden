"""
06_multi_tenant.py — Multi-Tenancy and Row-Level Security

Build a SaaS app where each organization has isolated data.
Uses row-level security (RLS) built into Eden.

Run:
    python examples/06_multi_tenant.py
"""

from eden import Eden, Model, StringField, IntField, ForeignKeyField, TenantMixin

app = Eden(title="Multi-Tenant SaaS", debug=True, secret_key="demo")
app.state.database_url = "sqlite+aiosqlite:///saas.db"

# Enable multi-tenancy middleware
app.add_middleware("tenant")


class Organization(Model):
    """SaaS tenant - maps to Tenant in Eden."""
    name = StringField(max_length=200)
    domain = StringField()


class User(Model, TenantMixin):
    """User belongs to an organization."""
    name = StringField(max_length=200)
    email = StringField()
    organization_id = ForeignKeyField(Organization)


class Document(Model, TenantMixin):
    """Document isolated per organization."""
    title = StringField(max_length=200)
    content = StringField()
    owner_id = ForeignKeyField(User)
    organization_id = ForeignKeyField(Organization)


@app.get("/documents")
async def list_documents(request):
    """
    List only documents for logged-in user's organization.
    TenantMixin automatically filters by organization_id.
    """
    org_id = request.tenant.id  # Current tenant from middleware
    docs = await Document.filter(organization_id=org_id).all()
    return {"documents": docs}


@app.post("/documents")
async def create_document(request):
    """
    Create document in current organization.
    organization_id automatically set by TenantMixin.
    """
    data = await request.json()
    doc = await Document.create(
        title=data["title"],
        content=data["content"],
        owner_id=request.user.id,
        organization_id=request.tenant.id  # Enforced here
    )
    return {"id": doc.id, "title": doc.title}


if __name__ == "__main__":
    app.setup_defaults()
    app.run(port=8000)

# What you learned:
#   - TenantMixin for automatic row-level isolation
#   - request.tenant for accessing current organization
#   - Automatic filtering by organization_id
#   - Multi-tenant security built in
#
# Next: See 07_production.py for deployment patterns
