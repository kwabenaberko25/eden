---
description: Critical checklist for auditing multi-tenancy isolation and authorization logic.
---

# Workflow: Security Audit

Use this workflow to perform deep-dive security reviews of the framework or application features.

## Steps

1. **Isolation Audit**:
    - `grep` for all models with `tenant_id` and cross-reference with `TenantMixin`.
    - Check view logic for any manual `session.execute` calls that might bypass `_base_select`.

2. **Authorization Review**:
    - Audit `routing.py` to identify all accessible routes.
    - Cross-reference routes with their corresponding view decorators (`roles_required`, etc.).
    - Verify that `is_superuser` is handled correctly as a bypass if intended.

3. **Data Integrity Check**:
    - Verify that Pydantic schemas in `forms.py` are not exposing sensitive internal fields for mass-assignment.
    - Ensure `HTMX` responses are correctly targeted and don't leak "out-of-band" data accidentally.

4. **Web Security Audit**:
    - Search for potential `dangerouslySetInnerHTML` equivalents or raw HTML injections.
    - Confirm CSRF middleware is active and `@csrf` tags are in all forms.
    - Check for secure link attributes on all external URLs.
