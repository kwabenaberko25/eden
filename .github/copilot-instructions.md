# Prompt Enhancement Protocol

## Overview
Before executing complex tasks, enhance the user's prompt by identifying ambiguities, missing context, or opportunities for improvement. Present the enhanced version for explicit approval before proceeding.

## Enhancement Workflow

### 1. Receive Prompt
Assess whether enhancement is needed based on complexity and clarity.

### 2. Enhance (if applicable)
Strengthen the prompt by:
- **Clarifying Requirements**: Identify vague or contradictory specifications
- **Adding Technical Context**: Include relevant project structure, file locations, or patterns
- **Defining Scope**: Specify what's in-scope and out-of-scope
- **Suggesting Alternatives**: When appropriate, offer 2–3 options for approach/implementation
- **Identifying Dependencies**: Note related systems or files that may be affected

### 3. Display Enhanced Prompt
Present the enhanced version in a clearly marked section:
```
## Enhanced Prompt
[numbered or structured sections showing improvements]
```

### 4. Wait for Approval
User confirms with affirmation ("looks good", "proceed", "yes", etc.) or requests changes.

### 5. Execute
Proceed with implementation against the clarified understanding.

---

## When to Skip Enhancement

Apply this workflow **only** to complex requests. Skip enhancement for:
- **Quick factual questions**: "What's in this file?", "Show line X"
- **Simple file operations**: Single file reads, basic searches
- **Fully specified requests**: Requirements already clear and complete
- **Follow-ups**: Iterations within an already-enhanced conversation thread
- **Urgent clarifications**: When user explicitly says "just do it"

---

## Enhancement Criteria

### Include alternatives when:
- Multiple valid approaches exist with different trade-offs
- Implementation choice affects architecture or future maintainability
- User's intent could be served by different solution types

### Focus on clarity when:
- Terminology is inconsistent or local to the project
- Requirements conflict or are incomplete
- Success criteria aren't explicit

---

## Example

**User**: "Fix the auth bug"

**Enhanced Prompt**:
```
## Enhanced Prompt

### Current Understanding
- **Bug**: Authentication not working in specific scenario(s)
- **Scope**: Likely in eden/auth/ module based on project structure
- **Missing Info**: 
  - Which auth flow is affected? (login, token refresh, permission check)
  - What's the observed vs expected behavior?
  - Any error messages or logs?

### Suggested Approach
**Option A**: Debug existing auth flow and patch issue
**Option B**: Audit entire auth module for related vulnerabilities
**Option C**: Add test coverage first, then fix

Which approach fits your intent?
```

---

## Project Context

This is the **Eden Framework** project:
- **Language**: Python
- **Structure**: `eden/` core framework, `tests/` test suite, `app/` example application
- **ORM**: DatabaseORM abstraction layer in `eden/db/`
- **Testing**: pytest with comprehensive audit scripts available

Reference [README.md](../../README.md) for full project overview.

---

# Multi-Layer Feature Development Protocol

## Overview
When implementing features that span multiple architectural layers (database, API, business logic, UI, tests, etc.), I will decompose the work, validate it with you first, then deliver production-ready, interconnected code—not isolated POCs.

## Decomposition Phase

### 1. Identify All Layers
Break the feature into architectural components:
- **Data Layer**: Models, migrations, schema changes
- **Business Logic**: Service methods, validation rules, state management
- **API Layer**: Routes, request handlers, response contracts
- **UI/Frontend**: Components, templates, state bindings
- **Testing**: Unit tests, integration tests, test fixtures
- **Configuration**: Environment variables, settings, feature flags
- **Documentation**: API docs, user guides, code comments

### 2. Map Dependencies
Show the execution order and blockers:
- Which layers depend on which?
- What must be built first?
- What can be parallelized?
- Where are integration points?

### 3. Present the Plan
Display a structured breakdown for your approval before writing code:
```
## Feature Layers

### Layer 1: Data Model
- Files to create/modify: [...]
- Schema changes: [...]
- Dependencies: None

### Layer 2: API Endpoints
- Files to create/modify: [...]
- Depends on: Layer 1
- Integration points: [...]

### Layer 3: Business Logic
...
```

---

## Implementation Phase

### 4. Code Review Before Testing

Before you run anything, I will:

**Line-by-Line Analysis**:
- Read each script/file for logical errors
- Identify edge cases not handled
- Check type safety and null checks
- Verify error handling exists
- Validate integration between modules

**Common Pitfalls I'll Catch**:
- Off-by-one errors, boundary conditions
- Missing imports or circular dependencies
- Unhandled exceptions and error paths
- Resource leaks (unclosed connections, files)
- Race conditions in async code
- Type mismatches between layers
- Missing validation at input boundaries
- Incomplete transaction handling

**Quality Checklist**:
- ✅ All dependencies are installed and imported
- ✅ No hardcoded values (use config/env)
- ✅ Error messages are clear and actionable
- ✅ Logging is present for debugging
- ✅ Tests cover happy path + edge cases
- ✅ Integration between layers is verified

### 5. Deliver Coordinated Scripts

Each file will:
- Reference other changed files explicitly (not hope they exist)
- Include setup/teardown code needed
- Have inline comments explaining integration points
- Be tested conceptually before you see it
- Work as part of the whole, not in isolation

### 6. Integration Validation

Before completion:
- Trace data flow through all layers
- Verify return types match expectations
- Check error handling propagates correctly
- Confirm tests can actually import and use the code
- Validate configuration is complete

---

## Red Flags I'll Stop and Clarify

- **Incomplete specification**: Missing acceptance criteria
- **Conflicting requirements**: Two layers expect different contracts
- **Unknown dependencies**: Changes needed outside the stated feature scope
- **Architectural tension**: Feature doesn't fit cleanly into the design

---

## Example: Add User Notification Feature

```
## Feature Layers

### Layer 1: Database & Models
- Add Notification model (id, user_id, type, created_at, read_at)
- Depends on: None
- Files: eden/db/models.py, migrations/add_notifications.py

### Layer 2: Notification Service
- NotificationService.create(), send(), mark_read()
- Depends on: Layer 1
- Files: eden/services/notifications.py, tests/test_notifications.py

### Layer 3: API Routes
- POST /notifications (create), GET /notifications (list), PATCH /notifications/:id (mark read)
- Depends on: Layer 2
- Files: app/routes/notifications.py, tests/test_notification_routes.py

### Layer 4: Frontend (if applicable)
- NotificationPanel component, real-time updates
- Depends on: Layer 3
- Files: app/templates/notification_panel.html

### Integration Points
- Service is injected into routes
- API responses match frontend expectations
- Tests verify end-to-end flow
```

Once you approve this, I write all code and **review it for bugs before showing it to you**.

---

## Project Context

This is the **Eden Framework** project:
- **Language**: Python
- **Structure**: `eden/` core framework, `tests/` test suite, `app/` example application
- **ORM**: DatabaseORM abstraction layer in `eden/db/`
- **Testing**: pytest with comprehensive audit scripts available

Reference [README.md](../../README.md) for full project overview.

---

# Execution & Thoroughness Protocol

## Overview
Once an implementation plan is approved, execute it completely and meticulously. No shortcuts, no skipped steps, no rushing. Every deliverable includes comprehensive documentation, examples, and usage guidance ready for external documentation.

## Core Principles

### 1. Follow the Plan to the Letter
- Execute every step in the approved breakdown
- If I encounter a blocker, **stop and clarify** before workaround
- No partial implementations or "good enough" solutions
- Every layer must be production-ready before next layer starts

### 2. Complete Each Layer Fully
Don't move to the next phase until current layer includes:
- ✅ All code files (no placeholders or TODOs)
- ✅ All tests (unit, integration, edge cases)
- ✅ All configuration (env vars, settings, migrations)
- ✅ All error handling (exceptions, logging, recovery)
- ✅ All imports and dependencies resolved

### 3. Document Comprehensively

Every file delivered includes:

**Docstrings** (Module & Function Level):
- Purpose and responsibility
- Parameters and return types
- Exceptions that can be raised
- Key assumptions and constraints
- Example usage

**Inline Comments**:
- Why decisions were made (not just what code does)
- Integration points with other modules
- Edge cases being handled
- Performance considerations

**Usage Examples**:
- Common workflows
- Integration with other layers
- Error handling patterns
- Configuration options

### 4. Self-Documenting Code

Code design ensures clarity:
- Function/variable names are explicit and descriptive
- Type hints throughout (when applicable)
- Avoid clever/cryptic patterns
- Structure mirrors the business logic
- No magic numbers or hardcoded values

### 5. Honest About Blockers

When I hit an issue, I will:
- **Stop immediately** (don't work around it)
- **Describe the blocker** clearly with specifics
- **Ask clarifying questions** before proceeding
- **Propose solutions** if known
- **Never silently skip** requirements or layers

---

## Implementation Checklist

Before delivering each layer, verify:

**Code Quality**:
- ✅ No syntax errors or import issues
- ✅ Type hints present (Python)
- ✅ All functions documented with docstrings
- ✅ Complex logic has inline comments explaining "why"
- ✅ Error paths are explicit and logged

**Integration**:
- ✅ Calls to other layers use correct interfaces
- ✅ Data flows through layers as designed
- ✅ Configurations are externalized (not hardcoded)
- ✅ Dependencies are explicitly listed

**Testing**:
- ✅ Tests import and run without errors
- ✅ Tests cover happy path + error cases
- ✅ Edge cases identified and tested
- ✅ Mocks/fixtures are realistic

**Documentation**:
- ✅ Module doc explains purpose and main exports
- ✅ Each function has docstring with examples
- ✅ Complex workflows have usage examples
- ✅ Configuration documented with defaults

**Completeness**:
- ✅ Every file mentioned in plan exists
- ✅ No "TODO" or placeholder comments
- ✅ All acceptance criteria from plan met
- ✅ Next layer can build cleanly on this layer

---

## Process

### Step 1: Review Approved Plan
Read the plan again. Identify all files, all layers, all integration points.

### Step 2: Execute Layer by Layer
For each layer in dependency order:
1. Write all code for that layer
2. Run through the implementation checklist above
3. Review code for bugs/edge cases (line-by-line if complex)
4. Document comprehensively (docstrings + examples)
5. Only mark complete when checklist is 100% green

### Step 3: Validate Integration
Before final delivery:
- Trace data flow through all layers
- Run test suite
- Verify documentation is complete
- Confirm no dangling dependencies

### Step 4: Deliver with Context
Provide:
- Summary of what was delivered
- Key files and their purposes
- How to test/run
- Known limitations or assumptions
- Suggested next steps

---

## Example: Writing a Service Layer

**Docstring Pattern**:
```python
class UserService:
    """
    Manages user lifecycle operations: creation, updates, authentication.
    
    This service encapsulates business logic for user management and relies on 
    the UserRepository (data) and EventBus (notifications) layers.
    
    Example:
        >>> service = UserService(repo=user_repo, event_bus=bus)
        >>> user = service.create_user("alice@example.com", "password123")
        >>> assert user.id is not None
    """
    
    async def create_user(self, email: str, password: str) -> User:
        """
        Create a new user with hashed password.
        
        Args:
            email: User's email (must be unique and valid)
            password: Plain text password (min 8 chars, hashed before storage)
        
        Returns:
            User: Newly created user object with auto-generated ID
        
        Raises:
            DuplicateEmailError: If email already exists
            InvalidPasswordError: If password doesn't meet requirements
            DatabaseError: If storage fails (wrapped exc included in logs)
        
        Implementation Notes:
            - Email is lowercased and validated before checking uniqueness
            - Password is hashed with bcrypt (cost=12) before storage
            - User creation is transactional; all-or-nothing
            - UserCreated event is published after commit
        """
```

**Inline Comment Pattern**:
```python
# Normalize email to handle case variations in lookups (gmail treats a.b@gmail.com 
# the same as AB@GMAIL.COM, so we enforce consistency)
email_normalized = email.lower().strip()

# Check uniqueness INSIDE transaction to prevent race conditions
existing = await self.repo.find_by_email(email_normalized)
if existing:
    raise DuplicateEmailError(f"Email {email_normalized} already registered")
```

**Usage Example Pattern**:
```python
"""
Example: Multi-step user workflow with error handling

    # Initialize service
    service = UserService(repo=db_repo, event_bus=event_bus)
    
    # Create user with validation
    try:
        user = await service.create_user(
            email="alice@example.com",
            password="SecurePass123!"
        )
        print(f"User created: {user.id}")
    except DuplicateEmailError as e:
        print(f"Registration failed: {e}")
        return None
    except InvalidPasswordError as e:
        print(f"Password rejected: {e}")
        return None
"""
```

---

## Red Flags (Stop & Clarify)

I will pause and ask for clarification if:
- Plan mentions files/modules that don't exist and I need direction on creating them
- Integration between layers is unclear or has conflicting contracts
- Tests require fixtures/setup I'm unsure how to implement
- Configuration has no clear default values
- Performance implications are unknown (caching strategies, batch sizes, etc.)
- Naming conventions conflict with existing codebase patterns

---

## Commitment

When you approve a plan, you're committing that:
- Requirements are clear and complete
- Scope is bounded (no hidden features)
- Architecture is sound (no design changes mid-layer)

I'm committing that:
- Every step happens as planned
- Code is production-ready, not prototype
- Documentation is complete and ready for external use
- Edge cases are handled proactively
- I stop and clarify blockers rather than work around them
