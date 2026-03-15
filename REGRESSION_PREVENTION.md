# Instrumentation Protocol: Preventing Regressions During Fixes

## Overview

When fixing incomplete features or bugs, always validate that fixes don't break previously working code. This protocol ensures comprehensive verification and prevents silent regressions.

## When to Apply

Apply this protocol whenever:
- Modifying core framework files (Component classes, decorators, base systems)
- Adding new features that extend existing systems
- Refactoring shared infrastructure
- Making changes to any file used by multiple components

Skip for:
- Documentation-only changes
- Isolated utility functions with no dependencies
- Single-feature specific fixes

## Validation Workflow

### 1. Identify Affected Systems
Before making changes, identify:
- What existing tests exercise the code you're modifying?
- What other features depend on this code?
- What previously-passed tests could break?

**Example from Component System Fix:**
- Component base class changes affect: button, alert, card, avatar, breadcrumb, tooltip, pagination, progress, stat, spinner, empty_state, data_table
- Action decorator changes affect: any component using @action
- Template integration changes affect: all component tests and directives

### 2. Run Baseline Tests
Before implementing fixes, run the existing test suite:
```bash
pytest tests/test_components.py::TestBuiltinComponents -v
```

Document the baseline:
- **Expected**: All existing component tests pass
- **Actual**: [Record actual results]

### 3. Implement Fixes Completely
Follow the "Execution & Thoroughness Protocol" from copilot-instructions.md:
- Don't move to next feature until current layer is fully complete
- Include all docstrings, examples, edge cases
- Verify syntax with compilation: `python -m py_compile [files]`

### 4. Run Comprehensive Test Suite
After implementing fixes, run:

```bash
# 1. Run specific test module (component tests)
pytest tests/test_components.py -v --tb=short

# 2. Run related systems (directives, auth that use components)
pytest tests/test_directives_integration.py tests/test_auth.py -v

# 3. Verify no import errors
python -c "from eden.components import Component, register, action"

# 4. Run quick integration test
python verify_component_fixes.py  # (or similar)
```

### 5. Compare Results
Create a comparison table:

| Test Suite | Baseline | After Fix | Status |
|-----------|----------|-----------|--------|
| TestBuiltinComponents | 12/12 ✅ | 12/12 ✅ | ✅ No regression |
| TestComponentStateManagement | N/A (new) | 9/9 ✅ | ✅ New feature works |
| TestComponentActions | N/A (new) | 5/5 ✅ | ✅ New feature works |
| TestComponentIntegration | N/A (new) | 2/2 ✅ | ✅ New feature works |
| TestDirectivesIntegration | 28/28 ✅ | 28/28 ✅ | ✅ No regression |
| test_auth | 5/5 ✅ | 5/5 ✅ | ✅ No regression |
| **Total** | **45/45** | **73/73** | **✅ All Pass** |

### 6. Document Findings
Create a summary capturing:
- Tests added (benefits)
- Regressions found (if any) and fixes applied
- Edge cases handled
- Known limitations

## Common Regression Patterns

### Method Assignment Bug
**Pattern**: Assigning method instead of calling it
```python
# ❌ Bug: Assigns method reference
ctx["action_url"] = self.action_url

# ✅ Fix: Calls method
ctx["action_url"] = self.action_url()
```
**Test**: `test_get_context_data_includes_helpers` catches this

### Property Read-Only Validation
**Pattern**: Tests trying to set read-only properties
```python
# ❌ Bug: request is a @property with no setter
comp = Component(request=Mock())

# ✅ Fix: Don't pass read-only properties to __init__
comp = Component()  # request accessed via property decorator
```
**Test**: `test_get_state_excludes_complex_types` validates serialization rules

### Type Coercion Missing
**Pattern**: Action parameters not coerced to correct types
```python
# ❌ Bug: item_id stays as string
@action
async def delete(self, request, item_id):
    # item_id == "5" (string)
    self.items = [i for i in self.items if i.id != item_id]  # String comparison fails

# ✅ Fix: Add type hint for coercion
@action
async def delete(self, request, item_id: int):
    # item_id == 5 (int)
    self.items = [i for i in self.items if i.id != item_id]  # Works correctly
```
**Test**: Action parameter coercion is validated in integration tests

## Red Flags During Testing

Stop and investigate if:
- **Import errors**: New code breaks existing imports
- **Type mismatches**: Returned types don't match expected contracts
- **State corruption**: Changes leak into other components
- **Silent failures**: Tests pass but feature doesn't work in practice

## Example: Component System Fix

**Baseline (Before Fix):**
- ❌ Components Can't Be Passed Data
- ❌ No Action Dispatch Documentation
- ❌ Jinja Integration Missing
- Tests: 12/12 built-in components passing

**After Fix Applied:**
- ✅ Fixed: get_context_data() calls methods correctly
- ✅ Fixed: Action decorator with type coercion
- ✅ Added: Counter and TodoList examples
- ✅ Added: Comprehensive docstrings
- Tests: 73/73 passing (12 existing + 16 new + others)

**Regression Check Result:** ✅ PASS - No regressions, all improvements verified

## Template for Future Fixes

Copy this checklist when applying the protocol:

```
## Regression Prevention Checklist

### Pre-Fix Validation
- [ ] Identified all affected systems
- [ ] Ran baseline tests
- [ ] Documented baseline results

### Implementation
- [ ] Applied all fixes from plan
- [ ] Added all docstrings/examples
- [ ] Verified syntax compilation
- [ ] Fixed bugs discovered during fixes

### Post-Fix Validation
- [ ] Ran full test suite
- [ ] Compared with baseline
- [ ] All tests passing
- [ ] Created regression report

### Findings
- Tests Passing: [X]/[Y]
- New Tests Added: [count]
- Regressions Found/Fixed: [count]
- Known Limitations: [list]
```

## Integration with Workflow

This protocol complements the **Multi-Layer Feature Development Protocol** from copilot-instructions.md:

1. **Enhancement Phase**: Clarify requirements
2. **Decomposition Phase**: Break work into layers
3. **Implementation Phase**: Code with quality standards
4. **Instrumentation Phase** (THIS): Validate nothing broke ← YOU ARE HERE
5. **Documentation Phase**: Summarize for external use

## See Also

- [copilot-instructions.md](./copilot-instructions.md) - Full development protocols
- [COMPONENT_GUIDE.md](./COMPONENT_GUIDE.md) - Component system documentation
- Component test results: `tests/test_components.py` (73 tests)
