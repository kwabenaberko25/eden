---
description: Standardized steps for expanding Eden framework documentation phases.
---

# Workflow: Expand Documentation (Elite Protocol)

Use this workflow to ensure every new or updated documentation file meets the "Premium" standard of excellence for the Eden framework.

## 🌿 Phase 1: Pure Source Discovery

1.  **Identify Target**: Choose the framework feature (e.g., `orm`, `auth`, `routing`) and its corresponding source file in `eden/`.
2.  **Extract Extraction**: 
    // turbo
    - Run the metadata extractor: `python .agent/skills/doc_generator/scripts/doc_extractor.py c:/PROJECTS/eden-framework/eden/<target_file>.py`.
    - Review the generated "API Data Sheet" to identify all classes, methods, and docstrings.
3.  **Cross-Reference**: Use `grep_search` to find real-world usage of these features in the `tests/` or `app/` directories to inform usage examples.

## ✍️ Phase 2: Structural Drafting

1.  **Select Template**: Use `.agent/skills/doc_generator/examples/guide_template.md` as the blueprint.
2.  **Theory to Prose**: Rewrite the extracted technical facts into a "Premium" narrative. Explain *why* a developer should use this feature and what problem it solves.
3.  **Synthesis**: Ensure every mandatory section is present (Quick Start, Conceptual Overview, API Reference).

## 💡 Phase 3: Usage Example Proliferation

1.  **Generate 'The Three'**: Create exactly three examples for every major feature:
    - **Basic**: Minimal setup for immediate success.
    - **Intermediate**: A common SaaS use case (e.g., "Filtering users by tenant").
    - **Advanced**: A complex "power-user" scenario (e.g., "Manual session management with transaction isolation").
2.  **Verify Code Accuracy**: Double-check that all provided code snippets actually match the framework's current API (use `grep` to verify).

## ✨ Phase 4: Aesthetic Polish & Verification

1.  **Apply Admonitions**: Add `[!TIP]`, `[!NOTE]`, or `[!IMPORTANT]` blocks to emphasize critical knowledge.
2.  **Visual Flow**: If logic is non-trivial, add a **Mermaid diagram** to visualize it.
3.  **Final Build**: 
    // turbo
    - Run `mkdocs build` to ensure zero syntax errors and clean cross-links.
    - Review the final Markdown structure for accessible, descriptive headings.
