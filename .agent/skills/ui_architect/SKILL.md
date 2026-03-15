---
name: UIArchitect
description: Enforces Eden's "Premium" design system and aesthetic standards in all UI components and templates.
---

# Skill: UIArchitect

This skill ensures that every user-facing component in the Eden framework adheres to the "Elite" design standards established in our development history.

## Core Design Tokens

Always reference `eden/design.py` for the source of truth, but prioritize these established tokens:

1. **Typography**:
    - **Primary Sans**: `Plus Jakarta Sans` (Modern, Professional).
    - **Headings**: `Outfit` or `Plus Jakarta Sans` (Semi-bold/Bold).
2. **Color Palette (Dark Mode First)**:
    - **Backgrounds**: `obsidian` (#0F172A) and `surface` (#1E293B).
    - **Primary Action**: `primary` (#2563EB).
    - **Success**: `success` (#10B981).
    - **Warning**: `warning` (#F59E0B).
3. **Surface & Effects**:
    - **Glassmorphism**: Use `bg-gray-800/90` with `backdrop-blur-md` and subtle `border-gray-700`.
    - **Elevation**: Use soft shadow-glows (e.g., `shadow-blue-500/20`) instead of hard black shadows.

## Interaction Principles

- **Micro-animations**: Every button and card should have a subtle hover response (e.g., `hover:scale-[1.02]` or `hover:translate-y-[-2px]`).
- **Transitions**: Use `transition-all duration-300` for all state changes to ensure a smooth, fluid feel.
- **Feedback**: Use HTMX indicators or localized loading spinners for all async actions.

## Guidelines

- **No Placeholders**: Never use generic colors or basic default fonts.
- **Semantic HTML**: Maintain clean, accessible HTML structures.
- **HTMX First**: Prioritize partial updates and reactive interactions using Eden's `@fragment` directive.
- **Modern Syntax**: Always use **brace-style directive syntax** (e.g., `@if(cond) { ... }`, `@for(item in items) { ... }`) for template control flow. Avoid legacy `@endif` or `@endfor` tags.
