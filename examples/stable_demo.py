"""
Eden 1.0 Stable Release Demo
Showcasing the unified API, multi-tenancy, and RBAC security.

Run:
    python examples/stable_demo.py
"""

import uuid
from eden import Eden, Router, Depends
from eden.orm import Model, Mapped, f
from eden.orm import AccessControl, AllowOwner, AllowRoles

# 1. Models with RBAC and Unified Aliases
# Note: In Eden 1.0, we prefer importing everything from 'eden.db'
class SecureDocument(Model, AccessControl):
    """
    A model demonstrating row-level security.
    Documents can only be read/updated by their owners.
    Only admins can delete them.
    """
    __tablename__ = "demo_documents"
    
    # RBAC rules defined declaratively
    __rbac__ = {
        "read": AllowOwner("user_id"),
        "update": AllowOwner("user_id"),
        "delete": AllowRoles("admin"),
    }
    
    id: Mapped[uuid.UUID] = f(primary_key=True, default_factory=uuid.uuid4)
    title: str = f(max_length=255)
    content: str = f()
    user_id: Mapped[int] = f(index=True)

# 2. Application Setup
app = Eden(
    title="Eden 1.0 Stable Demo",
    version="1.0.0",
    debug=True,
    secret_key="eden-demo-secret"
)

# 3. Multi-Tenancy Configuration
# By enabling the tenant middleware and setting a database URL,
# Eden will automatically isolate data per-tenant using Postgres search_path
# or global/tenant schema separation.
app.add_middleware("tenant")
app.state.database_url = "sqlite+aiosqlite:///demo.sqlite3"

# 4. Routes
@app.get("/")
async def root():
    """Welcome to Eden 1.0."""
    return {
        "framework": "Eden",
        "version": "1.0.0",
        "status": "Stable",
        "philosophy": "Modular Excellence"
    }

@app.get("/docs")
async def list_documents(request):
    """
    Example of retrieving documents filtered by the current user.
    The .for_user(user) method automatically applies the RBAC filters.
    """
    user = getattr(request.state, "user", None)
    if not user:
        return {"error": "Authentication required"}, 401
        
    # for_user() uses the __rbac__ rules defined on the model
    docs = await SecureDocument.query().for_user(user).all()
    return {"documents": [doc.to_dict() for doc in docs]}

# 5. Execution
if __name__ == "__main__":
    app.run()
