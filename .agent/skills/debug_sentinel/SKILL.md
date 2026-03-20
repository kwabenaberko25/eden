---
name: DebugSentinel
description: A high-fidelity, automated diagnostic suite for reproducing, isolating, and fixing complex framework bugs.
---

# Skill: DebugSentinel

`DebugSentinel` provides a "Mission-Ready" toolkit for deep diagnostics in the Eden framework. It automates manual "print-debugging" and boilerplate-heavy "reproduction script" creation.

## Core Capabilities

### 1. Isolated Reproduction (`repro_gen.py`)
- **What it does**: Creates a `repro_<name>.py` file that bootstraps a minimal, in-memory (or PostgreSQL) Eden environment, including specific models and database connectivity.
- **When to use**: When a bug is deep in the ORM or Auth and you need to isolate it from the full application stack.
- **Workflow**: `python .agent/skills/debug_sentinel/scripts/repro_gen.py --models="User, Profile" --failing-logic="logic.py"`

### 2. State-Trace Instrumentation (`trace_injector.py`)
- **What it does**: Injects formatted `print()` or `logging` statements before/after critical function calls to capture state snapshots (JSON-serialized if possible).
- **When to use**: When you don't know WHERE in a 100-line method the state is becoming corrupted.
- **Workflow**: `python .agent/skills/debug_sentinel/scripts/trace.py eden/db/fields.py:675 --var="self.relation"`

### 3. ORM Schema Inspector (`schema_check.py`)
- **What it does**: Compares the physical DB schema table definitions against the Python model classes to identify silent mismatches (e.g., missing indices, type differences).
- **When to use**: For "ProgrammingError" or "DataError" exceptions involving PostgreSQL.

### 4. Semantic Stress Tester
- **What it does**: Generates `pytest` test cases that specifically target "Evil Inputs" and boundary conditions (null handling, large decimals, circular relationships).

## Debugging Workflow (The "Sentinel Loop")

1. **Observe**: Capture the traceback and input parameters.
2. **Isolate**: Use `repro_gen.py` to create a standalone reproduction.
3. **Trace**: Inject state snapshots into the reproduction script to find the mutation point.
4. **Inspect**: Check the DB schema for physical mismatches.
5. **Fix & Stress**: Apply the fix and run the generated stress tests to ensure no regressions.
