# Audit System 📜

The Eden Audit System provides a high-level observability layer that tracks changes to your data and critical system events automatically.

## Overview

Unlike standard logging, the Audit System is **structured** and **persistent**. It records:
- **Who** performed the action (User/System).
- **What** changed (Model, Fields, Old vs New values).
- **When** it happened.
- **Context** of the action (IP address, Request ID, Tenant).

---

## Automatic Model Auditing

Enable auditing on any model by adding the `AuditableMixin`.

```python
from eden.db import Model, f, Mapped
from eden.audit import AuditableMixin

class Document(AuditableMixin, Model):
    title: Mapped[str] = f()
    content: Mapped[str] = f()
```

### What is tracked?
- **Create**: All initial values.
- **Update**: Only the specific fields that changed, including "before" and "after" snapshots.
- **Delete**: Record of deletion and final state.

---

## Manual Event Logging

You can record custom business events that aren't tied to a specific model change.

```python
from eden.audit import audit_log

@app.post("/export-data")
async def export_data(request):
    # Perform export logic...
    
    await audit_log(
        action="DATA_EXPORT",
        resource="UserRecords",
        details={"format": "csv", "count": 150},
        request=request
    )
```

---

## Viewing Audit Logs

Audit logs are stored in the `eden_audit_logs` table by default and can be viewed via the **Admin Panel**.

### Querying Programmatically
```python
from eden.audit import AuditLog

# Find all deletions by a specific user
logs = await AuditLog.filter(
    action="delete", 
    user_id=target_user_id
).all()
```

---

## Configuration

Control the retention and verbosity of logs in `eden.json`:

```json
{
    "audit": {
        "enabled": true,
        "retention_days": 90,
        "exclude_fields": ["password_hash", "token"],
        "async_logging": true
    }
}
```

- **Retention**: Automatically purges logs older than X days.
- **Exclusion**: Sensitive fields are never recorded in audit trails.
- **Async**: Logs are written in a background task to avoid slowing down requests.

---

## Security Compliance

Eden's audit trails meet most standard requirements for:
- **SOC2 Compliance**: Immutable record of sensitive data access.
- **HIPAA**: Tracking of PHI (Protected Health Information) access.
- **GDPR**: Record of data processing activities.

---

**Next Steps**: [Logging & Telemetry](logging.md)
