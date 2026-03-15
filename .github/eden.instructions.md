---
# Eden Framework Development Instructions

## Overview
These instructions guide development on the Eden Framework project. Follow them to maintain code quality, ensure tested implementations, and prevent regressions.

## Core Principles

### 1. Complete Before Moving On
- Don't mark a feature as done until ALL layers are implemented
- No "TODO" comments or placeholder code
- Each layer must be production-ready before the next begins

### 2. Test Before Declaring Success
- Write tests alongside code
- Run full test suite, not just new tests
- Compare results: baseline → after fix → regression check
- If any test breaks, fix it immediately

### 3. Document as You Go
- Docstrings with parameters, return types, exceptions
- Inline comments explaining "why", not just "what"
- Examples in docstrings showing common usage
- Keep documentation in code, not separate wiki

### 4. Prevent Regressions
- Always run existing tests before and after changes
- Use comprehensive test suites, not just targeted tests
- Document baseline metrics
- Report regression findings explicitly

## Typical Task Workflow

### Phase 1: Plan & Clarify
- [ ] Read user request
- [ ] Identify ambiguities
- [ ] Present enhanced prompt for approval
- [ ] Clarify scope and dependencies

### Phase 2: Decompose
- [ ] Break feature into architectural layers
- [ ] Map dependencies and blockers
- [ ] Plan test strategy
- [ ] Show plan for approval before coding

### Phase 3: Implement
- [ ] Code one layer at a time
- [ ] Verify syntax: `python -m py_compile [files]`
- [ ] Include comprehensive docstrings and examples
- [ ] Handle all error cases

### Phase 4: Test Comprehensively
- [ ] Run baseline tests (existing functionality)
- [ ] Run new tests (new functionality)
- [ ] Run related test suites (systems that depend on changes)
- [ ] Compare results and document findings

### Phase 5: Validate No Regressions
- [ ] Check that all existing tests still pass
- [ ] Verify new functionality works
- [ ] Review test results in detail
- [ ] Report any issues found and fixed

### Phase 6: Document Findings
- [ ] Create summary of what was delivered
- [ ] Include test pass/fail counts
- [ ] Note any regressions found and fixed
- [ ] Suggest next steps

## Templates for Quality

### Docstring Format
```python
def method_name(self, param1: Type1, param2: Type2) -> ReturnType:
    """
    Brief one-line description.
    
    Longer explanation if needed. Describe:
    - What the method does
    - When to use it
    - Key assumptions
    
    Args:
        param1: Description of parameter 1
        param2: Description of parameter 2
    
    Returns:
        ReturnType: Description of what's returned
    
    Raises:
        ExceptionType: When this exception is raised
    
    Example:
        >>> instance.method_name(value1, value2)
        expected_result
    """
```

### Test Structure
```python
class TestFeatureName:
    """Test [feature name] with focus on [aspect]."""
    
    def test_happy_path(self):
        """Feature works correctly with valid inputs."""
        # Setup
        # Execute
        # Assert
    
    def test_error_handling(self):
        """Feature handles errors gracefully."""
        # Setup invalid state
        # Verify exception raised
        # Verify error message clear
    
    def test_edge_cases(self):
        """Feature handles boundary conditions."""
        # Test empty, null, max values
```

### Test Results Report
```
## Test Results Summary

**Total Tests: X/Y Passing**

### Component Tests
- TestBuiltinComponents: 12/12 ✅
- TestComponentStateManagement: 9/9 ✅
- TestComponentActions: 5/5 ✅
- TestComponentIntegration: 2/2 ✅

### Regression Check
- Auth Tests: 5/5 ✅ (no regression)
- Directive Tests: 28/28 ✅ (no regression)

### Issues Found & Fixed
1. [Issue]: [Fix applied] - Verified with test [name]
2. [Issue]: [Fix applied] - Verified with test [name]

### Conclusion
✅ All fixes working correctly
✅ No regressions detected
✅ Production-ready
```

## Common Patterns & Pitfalls

### Avoid: Method Assignment
```python
# ❌ Wrong: Assigns reference to method
ctx["action_url"] = self.action_url

# ✅ Correct: Calls method
ctx["action_url"] = self.action_url()
```

### Avoid: Incomplete Type Coercion
```python
# ❌ Wrong: No type hint for coercion
@action
async def delete(self, request, item_id):
    # item_id is still a string from form data

# ✅ Correct: Type hint triggers coercion
@action
async def delete(self, request, item_id: int):
    # item_id is now an integer
```

### Avoid: Storing Complex Types in State
```python
# ❌ Wrong: User object won't serialize
def __init__(self, user):
    self.user = user  # Can't be JSON serialized

# ✅ Correct: Store ID, fetch when needed
def __init__(self, user_id):
    self.user_id = user_id
    
def get_context_data(self, **kwargs):
    ctx = super().get_context_data(**kwargs)
    ctx["user"] = self.fetch_user(self.user_id)
    return ctx
```

### Avoid: Silent Errors
```python
# ❌ Wrong: Error hidden
try:
    do_something()
except:
    pass  # Oops, bug invisible

# ✅ Correct: Log and handle
try:
    do_something()
except SpecificError as e:
    logger.error(f"Failed: {e}")
    raise
```

## Testing Commands Reference

```bash
# Run specific test class
pytest tests/test_components.py::TestComponentStateManagement -v

# Run entire test file
pytest tests/test_components.py -v

# Run multiple test files
pytest tests/test_components.py tests/test_auth.py -v --tb=short

# Run with coverage
pytest tests/ --cov=eden --cov-report=html

# Quick syntax check
python -m py_compile eden/module.py

# List all tests without running
pytest tests/ --collect-only -q

# Run with verbose output
pytest tests/ -vv --tb=long

# Stop on first failure
pytest tests/ -x --tb=short
```

## Definition of Done

A feature/fix is complete when:

- [ ] All code written and syntax-verified
- [ ] All docstrings present with examples
- [ ] All error handling in place
- [ ] New tests written and passing
- [ ] Existing tests still passing (regression check)
- [ ] Integration points validated
- [ ] Documentation updated (if needed)
- [ ] Findings documented with test results

## Getting Help

If you need to:
- **Find code**: Use Explore subagent for codebase exploration
- **Understand patterns**: Check existing code + docstrings
- **Debug tests**: Run with `-vv --tb=long` for detailed output
- **Verify syntax**: Use `python -m py_compile`
- **Check coverage**: Run pytest with `--cov` flag

## Project Structure Reference

```
eden/
  components/       # UI components, decorators
  db/              # ORM and database layer
  auth/            # Authentication system
  templating/      # Template system with directives
  context/         # Request context management
  
tests/
  test_components.py           # Component system tests
  test_directives_integration.py # Template directive tests
  test_auth.py                 # Auth system tests
  
COMPONENT_GUIDE.md            # Component system documentation
REGRESSION_PREVENTION.md      # This protocol
copilot-instructions.md       # Development protocols
```

## Examples of Well-Done Work

- **Counter Component** (`eden/components/counter.py`)
  - Complete docstrings with lifecycle
  - Type hints throughout
  - Multiple action methods with documentation
  - Template with examples
  - Tests covering state, actions, integration

- **Component System Tests** (`tests/test_components.py`)
  - TestComponentStateManagement (9 tests)
  - TestComponentActions (5 tests)
  - TestComponentIntegration (2 tests)
  - Pre-existing tests all passing (12 tests)

## Final Checklist

Before declaring a task complete:

- [ ] Read the requirements one more time
- [ ] Verify every stated requirement is met
- [ ] Run full test suite
- [ ] Review code for obvious bugs
- [ ] Check docstrings and examples are helpful
- [ ] Confirm no debug code or TODOs left
- [ ] Create summary of work delivered
- [ ] Call task_complete with summary

Then: Stop working and hand back to user.
