---
description: Standardized steps for expanding Eden framework documentation phases.
---

# Workflow: Expand Documentation

Use this workflow when expanding the Eden 10-phase documentation roadmap to ensure "Elite" quality.

## Steps

1. **Audit Existing Content**:
    - Identify target phase file (e.g., `docs/source/phase3.md`).
    - Review existing content for depth and accuracy.

2. **Sync with Source**:
    - Identify the corresponding `eden/` module (e.g., `router.py` for Phase 3).
    - Analyze the source for any undocumented features or changes.

3. **Technical Deep-Dive**:
    - Document internal mechanics, hooks, and advanced configuration options.
    - Ensure code examples are correct and follow current framework patterns.

4. **Premium Polish**:
    - Add structured alerts (`[!NOTE]`, `[!WARNING]`).
    - Standardize headings and link formatting.

5. **Verify and Build**:
    // turbo
    - Run `mkdocs build` to check for syntax errors.
    - Preview the generated HTML to ensure premium rendering.
