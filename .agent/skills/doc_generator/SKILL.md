---
name: DocGenerator
description: Analyzes Eden source code to generate and update premium documentation.
---

# Skill: DocGenerator

This skill enables the AI agent to maintain high-fidelity documentation for the Eden framework by directly analyzing the source code.

## Core Capabilities

1. **Source Analysis**: Use `view_file_outline` and `view_file` to understand ORM models, routing logic, and middleware implementations.
2. **Premium Synthesis**: Apply Eden's "Elite" documentation standards (premium aesthetics, senior-level depth) to generate Markdown guides.
3. **Consistency Guard**: Compare existing documentation in `docs/source/` with current code in `eden/` to identify and fix discrepancies.
4. **Visual Mapping**: Generate Mermaid diagrams to visualize complex logic like Row-Level RBAC or Multi-Tenancy resolution.
5. **Deep-Dive Specialized Training**:
    - **The Data Forge**: Document `QuerySet` expansions including `.annotate()`, `.aggregate()`, `Q` expressions (complex OR/NOT logic), and `F` expressions (database-level atomic updates).
    - **Directive Mastery**: Maintain guides for the `@if`, `@for`, `@auth`, and `@fragment` directives, ensuring perfect **brace-style syntax** (e.g., `@if(cond) { content }`) instead of legacy `@endif` markers.

## Guidelines

- **Senior-Level Depth**: Avoid basic summaries. Deep-dive into internals like `QuerySet` optimizations or dependency injection mechanics.
- **Aesthetic Excellence**: Use GitHub-style alerts (`[!TIP]`, `[!IMPORTANT]`) and maintain a structured, readable layout.
- **Verification**: Always verify documentation syntax with `mkdocs build` after generation.
