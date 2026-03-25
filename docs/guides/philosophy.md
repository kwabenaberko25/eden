# The Eden Philosophy: Why We Built This

> "The hardest part of building a modern SaaS shouldn't be the glue code."

In the modern Python ecosystem, building a production-ready application often feels like a puzzle. You need a fast API (FastAPI), an ORM (SQLAlchemy), a validation layer (Pydantic), a migration tool (Alembic), an authentication library (Authlib/Casbin), a tenancy strategy, and a form system.

By the time you've connected them all, you've written 1,000 lines of "glue code" that you have to maintain forever.

**Eden is different.** It's an **Integrated Framework**. We've done the glue work so you can do the feature work.

---

## 1. The "Pydantalchemy" Unified Model

In Eden, your Database Model *is* your Pydantic Schema. We've bridged the gap between SQLAlchemy and Pydantic so you only define your data once.

```python
from eden.db import Model, StringField, IntField

class Project(Model):
    name: str = StringField(max_length=100, index=True)
    budget: int = IntField(default=0)
    
    # Eden auto-generates the Pydantic schema behind the scenes.
    # From model to UI in one line:
    # form = Project.as_form(request.data)
```

## 2. Integrated Multi-Tenancy (Row & Schema)

Tenancy isn't an afterthought in Eden—it's at the core. Whether you need **Row-Level Isolation** (Shared Schema) or **Dedicated Schema Isolation** (Enterprise Data Privacy), Eden handles the context switching, filtering, and provisioning automatically.

- **Fail-Secure**: If you forget to filter by `tenant_id`, Eden returns an empty result set by default.
- **Dynamic Schemas**: Postgres `search_path` switching is built into the middleware.

## 3. Defense-in-Depth Security

Eden combines **Identity (Auth)**, **Multi-Tenancy (Isolation)**, and **Access Control (RBAC)** into a single, unified security layer.

No more checking `if user.is_owner` in every route. You define your rules on the model, and the ORM enforces them at the query level.

```python
class Document(Model):
    __rbac__ = {
        "view": ["user", "admin"],
        "edit": ["admin", AllowOwner()],
    }
```

## 4. Batteries Included, But Removable

Eden provides everything you need to go from `zero` to `deploy`:

- **Forms**: Auto-generated from models.
- **Storage**: Local, S3, and Cloudfront integration.
- **Emails**: SMTP, SES, and Resend with bulk-sending support.
- **Audit**: Request correlation IDs and automatic change tracking.

If you don't need a specific feature (like Tenancy), you don't use it. Eden is a **Scale-Up Framework**: it stays simple when you're small and grows with you as you reach enterprise scale.

---

**Next: [The Multi-Tenancy Master Class](multi-tenancy.md) →**
