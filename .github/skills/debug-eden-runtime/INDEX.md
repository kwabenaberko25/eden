# debug-eden-runtime Skill Index

**Fast, structured debugging for Eden Framework runtime errors.**

Complete reference for all documentation, templates, and tools in this skill.

---

## 🎯 Start Here

### New to This Skill?
1. Read [README.md](README.md) — Overview and quick start (5 min)
2. Skim [WHEN_TO_USE.md](WHEN_TO_USE.md) — Know when to invoke the skill (3 min)
3. Pick a template from [DEBUGGING_PROMPTS.md](DEBUGGING_PROMPTS.md) (2 min)
4. Share your error → Follow the workflow (varies)

### I Have a Specific Error
Go directly to [DEBUGGING_PROMPTS.md](DEBUGGING_PROMPTS.md) and find the matching template type.

### I Want to Understand the Framework
Read [references/eden-layers.md](references/eden-layers.md) for architecture overview.

---

## 📚 Main Documents

### [README.md](README.md)
**Quick start guide**

- What the skill does
- Complete workflow overview
- When to use each reference
- Example debugging session
- Common error patterns

**Read this first** if you're new to the skill.

---

### [SKILL.md](SKILL.md)
**The complete 5-step debugging workflow**

- **Phase 1: Reproduce** — Get repeatable error
- **Phase 2: Isolate** — Find which component fails
- **Phase 3: Inspect** — Understand root cause
- **Phase 4: Fix** — Apply targeted solution
- **Phase 5: Verify** — Confirm fix works

Each phase includes:
- Checklist
- Key questions
- Diagnostic techniques
- Examples
- Common patterns

**Read this** when you need detailed guidance through debugging.

---

### [WHEN_TO_USE.md](WHEN_TO_USE.md)
**Decision tree and integration guide**

- Should I use this skill or something else?
- How does this skill fit in my workflow?
- When to combine with other tools
- Symptom → Skill mapping
- Anti-patterns to avoid

**Read this** if you're unsure whether debugging is the right approach.

---

## 🛠️ Reference Guides

Located in `references/` directory

### [references/isolation-checklist.md](references/isolation-checklist.md)
**Layer-specific diagnostics**

Structured checklist for each architectural layer:
- **ORM Layer** — Queries, migrations, schema
- **Middleware Layer** — Auth, session, context
- **Templates Layer** — Directives, rendering, context
- **Async & Tasks** — Coroutines, context vars, event loop
- **Multi-Tenancy** — Tenant filtering, schema isolation
- **Auth Layer** — Tokens, decorators, permissions
- **WebSocket Layer** — Connections, messaging

Each section includes:
- Quick diagnostics
- Common issues
- Diagnostic code
- Choice tree for unknown layers

**Read this** when you need to find which layer the error is in.

---

### [references/common-pitfalls.md](references/common-pitfalls.md)
**12 known error patterns**

Common mistakes with examples and solutions:

**Critical Pitfalls** (high impact):
1. Missing await on async
2. Missing tenant context in query
3. Context var not set in async
4. Middleware not executing

**Medium Pitfalls**:
5. Type mismatch in query
6. N+1 query problem
7. Template directive undefined
8. Foreign key constraint violated

**Architectural Pitfalls**:
9. Dependency injection not used
10. Transaction scope incorrect

**Data & State**:
11. Datetime without timezone
12. Mutable default values

Each includes:
- Example of wrong vs. right
- Root cause explanation
- Diagnosis technique
- Prevention strategy

**Read this** if error matches a familiar pattern.

---

### [references/eden-layers.md](references/eden-layers.md)
**Architecture overview**

Explains each framework layer:
- ORM & Database
- Middleware & Request Handling
- Template Engine
- Task/Scheduler Layer
- Multi-Tenancy & Context
- Component & WebSocket Layer
- Cross-layer issues (async, circular deps)

Includes diagnostics for each layer.

**Read this** to understand how errors cross layers.

---

## 📋 Prompt Templates

### [DEBUGGING_PROMPTS.md](DEBUGGING_PROMPTS.md)
**Templates and examples for effective debugging prompts**

Templates for each phase:
- **Template 1**: Test failure
- **Template 2**: Isolate the layer
- **Template 3**: Inspect & root cause
- **Template 4**: Verify the fix

Each template includes:
- What to include
- Example filled out
- Anti-patterns to avoid

Checklists for each phase ensure you cover:
- ✅ All necessary context
- ✅ Evidence (logs, code, state)
- ✅ Clear questions

**Use this** when forming your debug prompt.

---

## 🔧 Scripts & Tools

Located in `scripts/` directory

### [scripts/isolate-test.py](scripts/isolate-test.py)
**Extract failing tests into standalone scripts**

Extract a failing test from test suite into a clean, runnable script for easier debugging.

**Usage**:
```bash
python scripts/isolate-test.py tests/auth/test_login.py::TestLogin::test_invalid_credentials
```

**Output**: `debug_test.py` — Standalone reproducer

**When to use**:
- Test fails in suite but you want to debug step-by-step
- Need to add breakpoints or detailed logging
- Test depends on complex fixtures you need to untangle

---

## 🎓 Learning Paths

### "I have a failing test"
1. [README.md](README.md) — Quick overview
2. [DEBUGGING_PROMPTS.md](DEBUGGING_PROMPTS.md) — Template 1
3. [SKILL.md](SKILL.md) — Follow Phase 1-5
4. [references/common-pitfalls.md](references/common-pitfalls.md) — Check if known pattern

### "I'm not sure which layer"
1. [references/isolation-checklist.md](references/isolation-checklist.md) — Layer-specific checks
2. [references/eden-layers.md](references/eden-layers.md) — Architecture overview
3. [DEBUGGING_PROMPTS.md](DEBUGGING_PROMPTS.md) — Template 2

### "Error seems urgent"
1. [WHEN_TO_USE.md](WHEN_TO_USE.md) — Is this a debugging issue?
2. [references/common-pitfalls.md](references/common-pitfalls.md) — Match to known pattern?
3. [DEBUGGING_PROMPTS.md](DEBUGGING_PROMPTS.md) — Copy template, provide context
4. Share with skill → Get guided through workflow

### "I'm new to the framework"
1. [references/eden-layers.md](references/eden-layers.md) — Understand architecture
2. [references/common-pitfalls.md](references/common-pitfalls.md) — Learn common mistakes
3. [references/isolation-checklist.md](references/isolation-checklist.md) — Learn diagnostics
4. Keep these handy for future debugging

---

## Quick Reference: File Organization

```
debug-eden-runtime/
│
├── README.md                          # Start here! Overview & quick start
├── SKILL.md                           # Main 5-step workflow (detailed)
├── WHEN_TO_USE.md                     # Decision tree & integration
├── DEBUGGING_PROMPTS.md               # Templates & examples
├── INDEX.md                           # This file
│
├── references/                        # Reference guides
│   ├── isolation-checklist.md        # Layer-specific diagnostics
│   ├── common-pitfalls.md            # 12 known error patterns
│   └── eden-layers.md                # Architecture overview
│
└── scripts/                           # Helper tools
    └── isolate-test.py               # Extract failing tests
```

---

## 🎯 By Situation: Find Your Answer

### I Have...
- **Error message?** → [README.md](README.md) quick reference table
- **Failing test?** → [DEBUGGING_PROMPTS.md](DEBUGGING_PROMPTS.md) Template 1
- **Unknown layer?** → [references/isolation-checklist.md](references/isolation-checklist.md)
- **Familiar pattern?** → [references/common-pitfalls.md](references/common-pitfalls.md)
- **Architecture question?** → [references/eden-layers.md](references/eden-layers.md)
- **Startup uncertainty?** → [README.md](README.md) example workflow
- **Should I use this skill?** → [WHEN_TO_USE.md](WHEN_TO_USE.md)
- **Prompt template?** → [DEBUGGING_PROMPTS.md](DEBUGGING_PROMPTS.md)
- **Complex test?** → [scripts/isolate-test.py](scripts/isolate-test.py)

---

## 📖 Reading Time Guide

| Document | Time | When to Read |
|----------|------|---|
| README.md | 5 min | First time or quick reminder |
| WHEN_TO_USE.md | 3 min | Unsure if you should debug |
| DEBUGGING_PROMPTS.md | 5 min | Formulating a debug question |
| SKILL.md (Phase 1) | 10 min | Starting to debug |
| SKILL.md (all phases) | 30 min | Deep dive or complex issue |
| common-pitfalls.md | 15 min | Learning patterns |
| isolation-checklist.md | 20 min | Need layer diagnostics |
| eden-layers.md | 15 min | Understanding architecture |

---

## 💡 Pro Tips

1. **Bookmark [DEBUGGING_PROMPTS.md](DEBUGGING_PROMPTS.md)** — Use templates every time
2. **Keep [common-pitfalls.md](references/common-pitfalls.md) handy** — Check it first for familiar patterns
3. **Use [isolate-test.py](scripts/isolate-test.py)** for complex tests — Saves time understanding fixtures
4. **Review [isolation-checklist.md](references/isolation-checklist.md)** when stuck — Methodical layer check
5. **Read [SKILL.md](SKILL.md) once fully** — Understand the complete workflow

---

## Integration with Other Skills

This skill works alongside:
- **agent-customization** — If you need to create debugging workflows
- **Explore** subagent — For codebase exploration (use before debugging)
- Standard coding help — For implementing fixes after diagnosis

---

## Feedback & Improvements

This skill is designed for the Eden Framework. If you find:
- Missing patterns in common-pitfalls.md?
- Layers not covered in isolation-checklist.md?
- Unclear instructions or examples?

Let me know, and I can enhance the skill with your learnings.

---

## Next Steps

1. **Pick your situation** from the quick reference above
2. **Go to the right document**
3. **Apply the workflow or template**
4. **Share your error** with the skill
5. **Follow the guided debugging**

Good luck! 🔍
