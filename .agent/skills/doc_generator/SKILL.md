---
name: DocGenerator
description: Analyzes Eden source code to generate and update premium, in-depth documentation with a major-framework feel.
---

# Skill: DocGenerator (Premium Edition)

This skill enables the AI agent to maintain high-fidelity documentation for the Eden framework by directly analyzing the source code. It prioritizes in-depth conceptual guides, extensive usage examples, and a premium "major framework" (e.g., FastAPI, Django) aesthetic.

## 🌿 The Eden Documentation Standard

Every piece of documentation generated must adhere to these "Elite" standards:

1.  **Usage-First Philosophy**: 
    - Every feature or concept MUST include at least **three varied usage examples**:
        - **Basic**: The simplest "Hello World" implementation.
        - **Intermediate**: A practical, real-world scenario (e.g., integrating with a database or multi-tenancy).
        - **Advanced**: Edge cases, performance optimizations, or deep-level customization.
2.  **Structural Integrity (Anatomy of a Guide)**:
    - **Header**: Descriptive title with a brief "premium" summary.
    - **Quick Start**: Getting the feature working in < 30 seconds.
    - **Conceptual Deep-Dive**: Explaining "The Why" behind the feature (not just "The How").
    - **Detailed API Reference**: Automatically extracted from docstrings and type hints.
    - **Troubleshooting & FAQs**: Addressing common pitfalls before they happen.
3.  **Aesthetic Excellence**:
    - **Admonitions**: Use GitHub-flavored alerts (`[!TIP]`, `[!NOTE]`, `[!IMPORTANT]`, `[!WARNING]`, `[!CAUTION]`) strategically.
    - **Hierarchy**: Clean `<h1>` through `<h3>` structure with descriptive, accessible heading names.
    - **Visual Aids**: Use Mermaid diagrams (`graph TD`, `sequenceDiagram`) for complex flows like authentication or task scheduling.

## 🛠️ Extraction Methodology

To ensure 100% accuracy, always source information **solely from the codebase**:

1.  **Discovery Phase**: Use `grep_search` to find every instance of a feature's usage in `eden/`.
2.  **Extraction Phase**: Run the `scripts/doc_extractor.py` helper script (if available) or use `view_file` to analyze:
    - **Docstrings**: The primary source for "what" and "how".
    - **Type Hints**: To document parameter types and return values correctly.
    - **Context Managers/Decorators**: To understand lifecycle and injection mechanics.
3.  **Synthesis Phase**: Combine code facts with "Premium" prose to create the guide.

## 🛡️ Consistency & Quality Guard

- **Content Preservation**: NEVER remove existing working examples, detailed explanations, or established patterns without a critical technical reason (e.g., a deprecated API).
- **Expansion vs. Replacement**: Always favor merging and expanding existing documentation over complete overwrites. If existing content is accurate but lacks the "Premium" tone, rewrite the prose while keeping the underlying technical examples.
- **No Placeholders**: Never use placeholder text or "TODO" in documentation.
- **Verification**: Always run `mkdocs build` after a significant documentation task.
- **Internal Cross-Linking**: Ensure new guides link back to related concepts (e.g., *ORM* linking to *Multi-Tenancy*).

## 🎓 Specialized Knowledge Areas

- **The Data Forge**: Documenting `QuerySet` expansions, `annotate`, `aggregate`, and complex `Q` expressions.
- **Directive Mastery**: Maintaining guides for `@if`, `@for`, `@auth`, and `@fragment` with correct **brace-style syntax**.
- **Real-Time Synergy**: Explaining the integration between `@eden_toasts`, `@eden_scripts`, and background tasks.
