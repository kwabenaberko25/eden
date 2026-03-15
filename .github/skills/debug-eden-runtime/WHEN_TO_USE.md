# When to Use the debug-eden-runtime Skill

Quick decision tree to know when to invoke this skill vs. other tools/approaches.

---

## Decision Tree

### Do you have a runtime error, test failure, or unexpected behavior?

```
Is there an error? (test fails, exception thrown, unexpected output)
│
├─ YES → Use debug-eden-runtime skill
│   │
│   ├─ Test failure? → Reproduce the test, isolate the layer
│   │
│   ├─ Production crash? → Capture error logs, reproduce locally
│   │
│   ├─ Async/concurrency issue? → Check for missing await, context vars
│   │
│   ├─ Multi-tenant data leak? → Check tenant filtering in queries
│   │
│   └─ "It used to work, now it doesn't"? → Check recent changes, known pitfalls
│
├─ NO → Is it a feature request or architectural question?
│   │
│   ├─ "How do I implement X?" → Use standard coding help
│   │
│   ├─ "What's the best pattern?" → Use design review or code review
│   │
│   └─ "Should I use X or Y?" → Use design discussion
│
└─ Unclear? → Debug first, design second
```

---

## Use Cases: When to Invoke

### ✅ Use This Skill

1. **Test Fails Locally**
   ```
   /debug-eden-runtime
   pytest tests/auth/test_login.py::test_invalid_password -xvs
   # Fails with: KeyError: 'user'
   ```

2. **Exception in Running App**
   ```
   /debug-eden-runtime
   Error when calling POST /api/users:
   AttributeError: 'NoneType' object has no attribute 'id'
   
   Full traceback: [...]
   ```

3. **Intermittent/Race Condition**
   ```
   /debug-eden-runtime
   Test works sometimes, fails other times.
   Might be async/context issue?
   ```

4. **Data Shows Wrong Results**
   ```
   /debug-eden-runtime
   User from tenant_a can see data from tenant_b.
   Multi-tenant isolation broken?
   ```

5. **Performance Degradation**
   ```
   /debug-eden-runtime
   Query takes 5s instead of 50ms.
   N+1 problem?
   ```

6. **Silent Failure (Expected X, Got Y)**
   ```
   /debug-eden-runtime
   Expected 10 users, got 5.
   Query filter not working?
   ```

---

## Don't Use This Skill For

### ❌ Not Applicable

1. **Design Question** ("Should I use FastAPI or Starlette?")
   → Use design discussion with main assistant

2. **Feature Implementation** ("How do I add authentication?")
   → Use standard coding help

3. **Documentation/Learning** ("Explain how the ORM works")
   → Use documentation or learning mode

4. **Code Review** ("Is this implementation good?")
   → Use code review mode

5. **Refactoring** ("How should I restructure this?")
   → Use refactoring help

6. **Optimization** ("Make this code faster")
   → Use performance optimization help (separate from debugging)

---

## When You Have Uncertainty

### "Should I use debug-eden-runtime or regular coding help?"

**Use debug-eden-runtime if**:
- There's an error or failure
- Behavior is unexpected or wrong
- You need to trace why something broke
- You're stuck on a test failure

**Use regular help if**:
- You're building something new
- You're designing or refactoring
- You're learning the framework
- You're asking how to do something

---

## Workflow: From Implementation to Debugging

```
Feature Development Workflow
│
├─ Design phase → Use design/architecture help
├─ Implementation → Use coding help
├─ Writing tests → Use test help
├─ Tests fail? → USE DEBUG-EDEN-RUNTIME ← YOU ARE HERE
│   │
│   ├─ Reproduce → Isolate → Inspect → Fix → Verify
│   │
│   └─ Tests pass? → Continue to next feature
└─ Done!
```

---

## Symptom → Skill Mapping

| Symptom | Skill | Why |
|---------|-------|-----|
| "Test fails at line 45" | debug-eden-runtime | Needs structured debugging |
| "I don't know how to write this test" | coding help | Design question |
| "Test is slow" | debug-eden-runtime | Performance issue (N+1) |
| "How do I mock this?" | coding help | Implementation help |
| "Wrong data returned" | debug-eden-runtime | Logic/query issue |
| "I'm not sure what to test" | test help | Test design |
| "Exception: KeyError: 'user'" | debug-eden-runtime | Runtime error |
| "Should I cache this?" | design help | Architecture |

---

## Depth of Help Provided

### debug-eden-runtime Focuses On

✅ **Root cause identification** (not just symptom fixing)  
✅ **Structured diagnostics** (checklist-driven)  
✅ **Layer-specific guidance** (ORM, middleware, async, etc.)  
✅ **Quick pattern matching** (known pitfalls)  
✅ **Verification** (ensuring fix is solid)  
✅ **Prevention** (why it happened, how to avoid)  

### What it Doesn't Cover

❌ "How do I implement X?" → Use coding help  
❌ "Teach me Python async" → Use learning resources  
❌ "Is this design good?" → Use code review  
❌ "Optimize this for 1M records" → Use performance help  

---

## Integration with Other Assistants

### Debugging + Coding Help

**Scenario**: Test fails, fix is unclear

```
1. Use debug-eden-runtime to identify root cause
   → "Missing tenant context in test fixture"
   
2. Use regular help to implement fix
   → "How do I add headers to test client?"
   
3. Use debug-eden-runtime to verify
   → "Confirm fix works and no regressions"
```

### Debugging + Design Discussion

**Scenario**: Recurring error pattern

```
1. Use debug-eden-runtime to examine pattern
   → "This keeps breaking in multi-tenant queries"
   
2. Use design help to solve systematically
   → "Should we auto-filter all queries by tenant?"
   
3. Use coding help to implement
   → "How do I add tenant filtering to QuerySet?"
   
4. Use debug-eden-runtime to verify no regressions
```

---

## When You're Stuck

### "I don't know if it's a bug or my understanding"

**Option 1**: Use debug-eden-runtime to reproduce and isolate
- Shows whether it's real bug or misunderstanding
- If bug: helps diagnose root cause
- If misunderstanding: clarifies the pattern

**Option 2**: Ask regular help for context
- "How does X feature work?"
- "What's the expected behavior?"

---

## Anti-Patterns: Don't Force It

### ❌ "I need to debug so I'll use debug-eden-runtime"
**Better**: "I have a failing test with this error, can you help me debug?"

### ❌ "I'll use debug-eden-runtime for all code help"
**Better**: Use the right tool for the right job

### ❌ "This is too complex for a skill"
**Better**: Use the skill's tools and references, ask for clarification if stuck

---

## Success Indicators

You're using the skill effectively if:

✅ **Error is identified and fixed**, not just patched  
✅ **Root cause understood**, not just symptom resolved  
✅ **Similar issues prevented**, not just this one solved  
✅ **Related tests still pass**, no regressions  
✅ **Took structured approach**, not random trial-and-error  

---

## Quick Reference: Yes/No Questions

| Question | Yes → Use Skill | No → Use Other Help |
|----------|---|---|
| Is there an error or failure? | Yes | No → design help |
| Is it a runtime issue? | Yes | No → design help |
| Do you know what the error is? | Partial → start here | No → reproduce first |
| Can you reproduce it? | Yes → skill | No → investigation help |
| Do you want to fix it? | Yes → skill | No → learn help |

---

## Next: Using the Skill Effectively

Once you decide to use debug-eden-runtime:

1. [Copy a template from DEBUGGING_PROMPTS.md](DEBUGGING_PROMPTS.md)
2. Fill in all sections
3. Include context (error, test, environment)
4. Ask specific questions
5. Let the skill guide you through the workflow

---

## Questions?

- **"How do I use the skill?"** → Read [README.md](README.md)
- **"What's the workflow?"** → Read [SKILL.md](SKILL.md)
- **"Give me a template"** → Use [DEBUGGING_PROMPTS.md](DEBUGGING_PROMPTS.md)
- **"Which layer?"** → Use [references/isolation-checklist.md](references/isolation-checklist.md)
- **"Known error pattern?"** → Check [references/common-pitfalls.md](references/common-pitfalls.md)
