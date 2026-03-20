---
description: Comprehensive diagnostic loop for reproducing, isolating, and fixing framework bugs in the Eden framework.
---

# Workflow: DebugSentinel Diagnostic Loop

Follow this loop when addressing complex bugs, regressions, or unexpected framework behavior.

## Phase 1: Observation
1. **Analyze Traceback**: Identify the exact line and Exception type.
2. **Determine Scope**: Is it a core ORM issue, an Auth logic break, or a routing failure?

## Phase 2: Isolation
// turbo
1. **Generate Reproduction**: Create a standalone reproduction script.
   ```powershell
   python .agent/skills/debug_sentinel/scripts/repro_gen.py --name "orm_bug" --models "models_path" --logic "failing_logic"
   ```
2. **Verify Failure**: Run the generated script (`python tmp/repro_orm_bug.py`) to confirm it fails with the SAME error as the main app.

## Phase 3: Trace & Isolate
// turbo
1. **Inject Traces**: For any suspect variable, inject a state snapshot.
   ```powershell
   python .agent/skills/debug_sentinel/scripts/trace_injector.py <filepath> --line <line> --var <var_name>
   ```
2. **Iterate**: Run reproduction, observe trace, adjust trace injection point until mutation/corruption is found.

## Phase 4: Fix & Verify
1. **Apply Fix**: Patch the code in the framework core.
2. **Verify Isolation**: Run the reproduction script to confirm the fix.
// turbo
3. **Clean Up**: Restore the files from their backups.
   ```powershell
   python .agent/skills/debug_sentinel/scripts/trace_injector.py <filepath> --restore
   ```
4. **Stress Test**: Generate a set of `pytest` test cases that specifically target boundary conditions based on the fixed logic.

## Phase 5: Final Check
1. **Run Full Suite**: Ensure no regressions by running the original failing tests.
   ```powershell
   pytest tests/test_orm_enhanced.py
   ```
