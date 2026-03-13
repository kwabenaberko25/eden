# Eden Templating Engine - Quick Reference

## 📌 Executive Overview

**Goal:** Build a custom, production-ready templating engine for Eden (separate from main eden/ package)

**Timeline:** 4-5 weeks (5 phases)

**Project Location:** `c:\ideas\eden\eden_engine\`

**Key Libraries Used:**
- `lark` — Grammar parsing (lexer + AST generation)
- `simpleeval` — Safe expression evaluation  
- `markupsafe` — HTML escaping
- `Python ast` — Code generation to bytecode
- `Jinja2` — Filter system (optional reuse)

---

## 🎯 Core Deliverables

### **Phase 1: Foundation & Parsing (Week 1-1.5)**
- **Deliverable:** Lark grammar + Tokenizer + AST nodes + Parser
- **Tests:** 80+ tokenization, 100+ parser tests
- **Key File:** `grammar/eden_directives.lark`

### **Phase 2: Code Generation & Runtime (Week 2-2.5)**
- **Deliverable:** AST→Python code compiler + Expression evaluator + All 40+ directives
- **Tests:** 200+ runtime tests
- **Key Files:** `compiler/codegen.py`, `runtime/directives/`

### **Phase 3: Engine Integration & Must-Haves (Week 3-3.5)**
- **Deliverable:** Main EdenEngine class + Caching + Loader + **New Features**:
  - Test functions (is defined, is empty, is odd)
  - Block inheritance (@extends, @block enhancement)
  - Namespaced imports (@import ... as ...)
  - Type hints (context schemas)
  - Safe mode (restrict directives/filters)
- **Tests:** 300+ integration tests
- **Key Files:** `engine/template_engine.py`, `runtime/tests.py`, `sandbox/safe_mode.py`

### **Phase 4: Optimization & Polish (Week 4-4.5)**
- **Deliverable:** Performance optimization + 30+ pages docs + 6 examples + Migration tool
- **Benchmarks:** < 10ms render time, < 100KB memory per template
- **Key Files:** `docs/`, `examples/`, `scripts/migration_tool.py`

### **Phase 5: Testing & Deployment (Week 5)**
- **Deliverable:** 500+ comprehensive tests + Security audit + Production-ready
- **Coverage:** > 95% line coverage
- **Key Outcome:** Ready to merge/use in Eden

---

## 📁 Project Directory Structure

```
eden_engine/
├── grammar/
│   ├── eden_directives.lark    # Complete PEG grammar
│   └── grammar_tests.py         # Validate grammar
│
├── lexer/
│   ├── tokenizer.py             # Lark-based lexer
│   └── test_tokenizer.py
│
├── parser/
│   ├── ast_nodes.py             # 40+ AST node types
│   ├── parser.py                # Token → AST builder
│   ├── namespaces.py            # Namespace resolution
│   └── test_parser.py
│
├── compiler/
│   ├── codegen.py               # AST → Python bytecode
│   ├── optimizer.py             # Performance passes
│   └── test_codegen.py
│
├── runtime/
│   ├── context.py               # Scope management
│   ├── evaluator.py             # Expression evaluation (simpleeval-based)
│   ├── filters.py               # Built-in filters + registry
│   ├── tests.py                 # Test functions (is defined, is odd, etc)
│   ├── directives/              # Handlers for all 40+ directives
│   │   ├── __init__.py          # DirectiveRegistry
│   │   ├── control_flow.py      # @if, @for, @unless, @switch
│   │   ├── components.py        # @component, @slot
│   │   ├── inheritance.py       # @extends, @block, @yield, @super
│   │   ├── forms.py             # @csrf, @checked, @selected
│   │   ├── routing.py           # @url, @active_link
│   │   ├── auth.py              # @auth, @guest, @htmx
│   │   ├── assets.py            # @css, @js, @vite
│   │   ├── data.py              # @let, @old, @json, @dump
│   │   └── messages.py          # @error, @messages
│   └── test_runtime.py
│
├── engine/
│   ├── template_engine.py       # Main EdenEngine class
│   ├── cache.py                 # Template caching + mtime tracking
│   ├── loader.py                # File loader + path resolution
│   ├── exceptions.py            # Custom exception types
│   └── test_engine.py
│
├── types/
│   ├── schemas.py               # TypedDict utilities
│   ├── validator.py             # Runtime context validation
│   └── test_types.py
│
├── sandbox/
│   ├── safe_mode.py             # Restricted execution mode
│   └── test_safe_mode.py
│
├── scripts/
│   ├── benchmark.py             # Performance profiling
│   ├── migration_tool.py        # Jinja2 → EdenEngine converter
│   └── playground.py            # Interactive REPL
│
├── examples/
│   ├── basic.py, components.py, inheritance.py
│   ├── type_hints.py, safe_mode.py
│   └── templates/               # Example template files
│
├── tests/
│   ├── unit/, integration/, performance/
│   ├── security/, edge_cases/
│   └── fixtures/
│
├── docs/
│   ├── ARCHITECTURE.md          # Design overview
│   ├── DIRECTIVES_REFERENCE.md  # All 40+ directives
│   ├── GRAMMAR.md               # Grammar explained
│   ├── API_REFERENCE.md         # Engine API
│   ├── MIGRATION_GUIDE.md       # Jinja2 → Eden
│   └── Performance.md           # Benchmarks + tips
│
├── pyproject.toml               # Package metadata
├── pytest.ini                   # Test config
├── README.md                    # Quick start
├── IMPLEMENTATION_LOG.md        # Daily progress (updated during dev)
└── dev-notes.md                 # Architecture decisions
```

---

## 🔑 Key Features to Implement

### **All 40+ Existing Directives**
✅ Control Flow: @if, @unless, @for, @switch/@case, @else/@elif/@empty  
✅ Loop Helpers: @even, @odd, @first, @last  
✅ Auth: @auth, @guest, @htmx, @non_htmx  
✅ Inheritance: @extends, @include, @block/@section, @yield, @super, @push/@stack  
✅ Forms: @csrf, @checked, @selected, @disabled, @readonly  
✅ Routing: @url, @active_link  
✅ Data: @let, @old, @span, @json, @dump  
✅ Assets: @css, @js, @vite  
✅ Components: @component, @slot, @render_field  
✅ Messages: @error, @messages  
✅ Special: @method, @eden_head, @eden_scripts, @fragment

### **Must-Have New Features**

#### **1. Test Functions** (from Tera)
```html
@if (user.email is defined) { ... }
@if (items is empty) { ... }
@if (count is odd) { ... }
@if (count is divisible_by(3)) { ... }
```

#### **2. Block Inheritance** (improved @extends)
```html
@extends "layouts/base"
@block content { ... }
@block head { @super { /* append */ } }
```

#### **3. Namespaced Imports** (from Tera)
```html
@import "components/cards" as card
@component(card.button, label="Click") { }
```

#### **4. Type Hints in Context**
```python
class PageContext(TypedDict):
    user: UserContext
    posts: List[Post]

engine.set_context_schema(PageContext)
# Now IDE can autocomplete context.user.name
```

#### **5. Safe Mode** (restrict untrusted templates)
```python
safe_config = {
    'allowed_directives': ['if', 'for', 'component'],
    'allowed_filters': ['uppercase', 'lowercase', 'truncate'],
    'no_method_calls': True
}
html = engine.render_safe('user_template.html', context, safe_config)
```

---

## 📊 Test Coverage Target

| Area | # Tests | Coverage |
|------|---------|----------|
| Directives (40+) | 150 | 100% |
| Expression Eval | 120 | >95% |
| Components/Slots | 80 | >95% |
| Block Inheritance | 60 | 100% |
| Error Handling | 70 | >95% |
| Safe Mode | 50 | 100% |
| Type Validation | 40 | >90% |
| Performance | 30 | Baseline |
| Edge Cases | 40 | >95% |
| **Total** | **~500** | **>95%** |

---

## ⏱️ Weekly Breakdown

| Week | Phase | Key Milestones |
|------|-------|-----------------|
| 1-1.5 | Foundation | Grammar + Lexer + Parser (100+ tests) |
| 2-2.5 | Runtime | CodeGen + Expression evaluator + 40+ directives (200+ tests) |
| 3-3.5 | Engine | EdenEngine + Must-haves (300+ integration tests) |
| 4-4.5 | Polish | Docs + Examples + Migration tool + Benchmarks |
| 5 | Testing | 500+ tests + Security audit + Production ready |

---

## 🎬 Getting Started (Phase 1)

### **Day 1-2: Setup**
- [ ] Create eden_engine/ directory structure
- [ ] Install dependencies: `pip install lark simpleeval markupsafe`
- [ ] Set up pytest + git repo
- [ ] Create IMPLEMENTATION_LOG.md

### **Day 3-5: Grammar Definition**
- [ ] Write complete Lark grammar (`eden_directives.lark`)
- [ ] Define all directiive patterns (@if, @for, @component, etc)
- [ ] Write 50+ grammar test cases
- [ ] Validate grammar compiles without errors

### **Day 6-7: Tokenizer**
- [ ] Wrap Lark into EdenLexer class
- [ ] Implement tokenize() method
- [ ] Track line/column info
- [ ] Write 80+ tokenization tests

### **Day 8-10: Parser**
- [ ] Define all AST node classes (40+)
- [ ] Write EdenParser class
- [ ] Parse token stream → AST
- [ ] Write 100+ parser tests

### **Phase 1 Exit Criteria**
- ✅ Grammar complete and documented
- ✅ 80+ tokenization tests passing
- ✅ 100+ parser tests passing
- ✅ All 40+ directive types recognized

---

## 🚦 Success Metrics

### **Performance**
- ✅ Simple template: < 1ms render
- ✅ Complex template: < 10ms
- ✅ Memory: < 100KB per cached template
- ✅ Cache hit rate: > 95% in typical workloads

### **Quality**
- ✅ > 95% line coverage
- ✅ > 90% branch coverage
- ✅ 0 known security vulnerabilities
- ✅ All 40+ directives functional

### **Documentation**
- ✅ 30+ pages of docs
- ✅ 6+ working examples
- ✅ Migration guide complete
- ✅ API reference complete

### **Integration**
- ✅ Works with Eden auth, ORM, routing
- ✅ No breaking changes
- ✅ Optional deployment (can test side-by-side with Jinja2)
- ✅ Easy rollback if issues arise

---

## 🔗 Related Files

- **Full Plan:** [EDEN_TEMPLATING_ENGINE_IMPLEMENTATION_PLAN.md](EDEN_TEMPLATING_ENGINE_IMPLEMENTATION_PLAN.md)
- **Existing Directives:** [docs/guides/DIRECTIVES_USAGE_GUIDE.md](docs/guides/DIRECTIVES_USAGE_GUIDE.md)
- **Audit Report:** [DIRECTIVES_AUDIT_FINAL_REPORT.md](DIRECTIVES_AUDIT_FINAL_REPORT.md)

---

**Ready to code? Start with Phase 1. Questions? Refer to the full implementation plan.**
