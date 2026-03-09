---
description: Comprehensive SOP for implementing a new full-stack feature in the Eden framework.
---

# Workflow: Implement Feature

Follow this "Standard Operating Procedure" to ensure every feature is built the "Eden Way."

## Phases

1. **Model & Forge (The Core)**:
    - Define the model in `models.py` or a dedicated module.
    - Inherit from `EdenModel` and `TenantMixin` (if applicable).
    - Run the Forge migration audit.

2. **Pydantic & Forms (The Input)**:
    - Create a Pydantic schema for validation.
    - Define a `BaseForm` in `forms.py` using the schema.
    - Apply custom widgets or attributes using the "Premium" method chaining API.

3. **Views & Controllers (The Logic)**:
    - Create an async view function in `views.py`.
    - Use `roles_required` if the feature is restricted.
    - Fetch data using the ORM (e.g., `User.all()`).
    - Return a `templates.template_response`.

4. **Templates & UI (The Interface)**:
    - Create a template using Eden's `@directive` syntax.
    - Use `@extends` for standard layouts.
    - Apply `UIArchitect` standards for colors, typography, and motion.
    - Integrate HTMX for reactive parts (e.g., `@fragment`).

5. **Verification**:
    - Run the `verify_implementation` workflow.
    - Run the `security_audit` workflow.
