# Eden Quality Standards: The Golden Rules

This document defines the non-negotiable quality and completeness standards for all development within the Eden Framework. Every contribution, whether a new feature or a bug fix, must adhere to these rules.

---

## 1. Zero-Placeholder Policy (Absolute Completeness)
We do not ship partial logic or "work in progress" markers.
- **NEVER** use `NotImplementedError`, `TODO`, `FIXES`, or `TBD`.
- **NEVER** use `pass` as a placeholder for actual logic.
- **ALWAYS** implement the full logic for every branch, edge case, and error path before declaring a task finished.
- **NEVER** leave "scaffolded" methods empty. If a method is defined, it must be functional and tested.

## 2. Layered Verification (Rigor)
Quality is verified at every step, not just at the end.
- **ALWAYS** run tests after completing each architectural layer (e.g., Data -> Logic -> API -> UI).
- **NEVER** move to Layer B until Layer A is 100% verified and bug-free.
- **ALWAYS** include unit tests for core logic and integration tests for cross-layer functionality.

## 3. Scope Preservation (Focus)
Respect the existing codebase by maintaining strict focus.
- **ALWAYS** stay within the boundaries of the assigned task.
- **NEVER** refactor or modify code that is unrelated or unconnected to the current project objectives.
- **AVOID** "opportunistic" changes to core systems (like the ORM or Templating engine) unless the task explicitly requires it.
- **ALWAYS** justify any change to shared infrastructure in the implementation plan.

## 4. Premium Documentation (Contextual Clarity)
Code must be self-documenting and provide immediate value to other developers.
- **ALWAYS** use Google-style docstrings for classes and methods.
- **ALWAYS** include an `Attributes` or `Args` section with explicit types and descriptions.
- **ALWAYS** provide a "Real-world" usage example in the docstring (using `>>>` notation where possible).
- **ALWAYS** explain the "Why" in complex logic using inline comments, not just the "What".

## 5. Production-Ready DX (Developer Experience)
We deliver solutions, not just code snippets.
- **ALWAYS** ensure changes "just work" out of the box with zero additional configuration required from the user.
- **ALWAYS** prioritize clean, readable, and idiomatic Python code.
- **ALWAYS** treat the developer using our framework as a VIP—every error message should be actionable and every API should be intuitive.

---

## The "Golden Standard" Checklist

Before submitting any work, verify against this list:

- [ ] **No placeholders**: I have searched for `TODO`, `pass`, and `NotImplemented`.
- [ ] **Fully Functional**: Every new function/class performs its intended purpose 100%.
- [ ] **Documented**: Every public entity has a docstring with an example.
- [ ] **Tested**: I have run tests for the current layer and verified no regressions.
- [ ] **Focused**: I have not touched files or logic unrelated to the task.
- [ ] **DX Verified**: I have manually traced or run an example to ensure the experience is premium.
