---
name: SecurityAuditor
description: Audits Eden code for security vulnerabilities, focusing on multi-tenancy isolation and authorization logic.
---

# Skill: SecurityAuditor

This skill is dedicated to maintaining the "Fortress" integrity of the Eden framework, specifically focusing on data isolation and reliable access control.

## Core Responsibilities

1. **Multi-Tenancy Isolation**:
    - **Mixin Check**: Ensure every model that should be tenant-scoped inherits from `TenantMixin`.
    - **Context Leakage**: Verify that queries are not bypassing the automatic `_base_select` filters.
    - **Creation Safeguard**: Confirm `before_create` hooks are correctly setting `tenant_id`.

2. **Authorization & RBAC**:
    - **Decorator Audit**: Ensure `roles_required` and `permissions_required` are applied to all sensitive entry points.
    - **Policy Integrity**: Audit `__rbac__` configurations on models for logical consistency (e.g., `AllowOwner` is correctly implemented).

3. **General Security**:
    - **Safe Redirection**: Prevent direct `window.location` assignments; enforce high-level redirection helpers.
    - **CSRF & Tokens**: Verify CSRF protection is active on all interactive forms.
    - **External Links**: Enforce `rel="noopener noreferrer"` for all `target="_blank"` links.

## Audit Workflow

- **Manual Spot-Check**: Periodically review sensitive modules like `auth/` and `tenancy/`.
- **Code Change Review**: Every change to models or views must be audited for potential isolation breaks.
- **Tooling**: Use static analysis patterns to find "orphaned" models (models with `tenant_id` but missing the mixin logic).
