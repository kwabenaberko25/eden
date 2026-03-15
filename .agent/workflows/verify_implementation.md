---
description: Run core verification tasks to ensure implementation integrity.
---

# Workflow: Verify Implementation

Use this workflow to validate code changes, run tests, and perform linting audits.

## Steps

1. **Linting Audit**:
    // turbo
    - Run `ruff check eden/` to identify code quality issues.
    - Run `ruff format eden/ --check` to verify formatting consistency.

2. **Test Suite Execution**:
    // turbo
    - Run `pytest tests/ -v` to ensure all unit and integration tests pass.
    - Check for any performance regressions or breaks in core logic (ORM, Routing).

3. **Structure Validation**:
    - Verify that no illegal/temp files were added to the root (e.g., `tmp_`, `test_`).
    - Ensure all new files follow Eden's directory structure conventions.

4. **Security Check**:
    - Specifically verify that new features don't bypass Multi-Tenancy or RBAC protections.
    - Look for potential CSRF or unsafe redirection vulnerabilities.
