# Eden Templating Engine - Phase 1 Kickoff Checklist
## Implementation Ready to Begin

**Status:** ✅ READY FOR PHASE 1 START  
**Last Updated:** March 13, 2026  
**Target Start:** Immediately  
**Phase 1 Duration:** Weeks 1-1.5 (5-7 days estimated)

---

## Executive Summary

All design and planning complete. The Eden Templating Engine specification is finalized with:
- **40+ directives** fully catalogued
- **Consistent Option A syntax** approved: `@directive(args) { body }`
- **Comprehensive testing strategy** emphasizing **1,350+ tests** (3x original plan)
- **Form directives fully integrated** including @render_field for all field types
- **Project structure** ready to implement

---

## What's Been Completed ✅

### Design & Architecture
- ✅ 5-phase implementation plan (complete spec)
- ✅ Option A syntax standardized and approved
- ✅ All 40+ directives documented
- ✅ Form directives added (render_field, csrf, checked, selected, etc)
- ✅ 8 real-world template examples (all using Option A)
- ✅ 1 comprehensive form page example

### Documentation
- ✅ EDEN_TEMPLATING_ENGINE_IMPLEMENTATION_PLAN.md (50+ pages)
- ✅ EDEN_SYNTAX_STANDARD_FINAL.md (all directives)
- ✅ EDEN_TEMPLATING_ENGINE_EXAMPLES_OPTION_A.md (9 examples)
- ✅ EDEN_ENGINE_QUICK_REFERENCE.md (quick lookup)

### Testing Strategy
- ✅ Comprehensive test structure defined (1,350+ tests total)
- ✅ Form testing plan (140+ form-specific tests)
- ✅ Filter testing plan (90+ built-in filter tests)
- ✅ Performance benchmarking included
- ✅ Security testing (CSRF, injection prevention)
- ✅ Edge case coverage specified

---

## Phase 1: Foundation & Parsing (STARTING NOW)

**Duration:** 5-7 days (concurrent with other work)  
**Goal:** Lexer → Parser → AST generation complete

### 1.1 Grammar Definition (`eden_directives.lark`)

**Deliverables:**
- [x] Specification of grammar rules
- [ ] Lark grammar file implementation
- [ ] Grammar validation tests (50+)

**Key Areas:**
- All 40+ directives with proper syntax
- Form directives: @render_field with options dict
- Expressions, filters, test functions
- Nested block parsing

**Test Cases to Implement:**
```python
# tests/unit/grammar_tests.py
- 50+ grammar validation tests
- Test each directive syntax
- Test nested combinations
- Test error cases (malformed input)
```

---

### 1.2 Tokenizer (`lexer/tokenizer.py`)

**Deliverables:**
- [ ] EdenLexer class (Lark-based)
- [ ] 80+ tokenization tests

**Key Methods:**
- `tokenize(template_str)` → List[Token]
- `get_line_number(pos)` → int
- `get_column_number(pos)` → int

**Test Coverage:**
```python
# tests/unit/test_tokenizer.py (80+ tests)
- Tokenize control flow (@if, @for, etc)
- Tokenize components (@component, @slot)
- Tokenize forms (@csrf, @render_field, etc)
- Tokenize expressions ({{ }})
- Preserve line/column info
- Handle nested blocks
```

---

### 1.3 AST Nodes (`parser/ast_nodes.py`)

**Deliverables:**
- [ ] 40+ AST node types
- [ ] Base ASTNode class
- [ ] Node factory functions

**Node Types:**
- ControlFlowNode (if, unless, for, switch)
- ComponentNode, SlotNode
- InheritanceNode (extends, block, yield)
- FormNode (for form directives)
- ExpressionNode, FilterNode, TestNode
- Special nodes (push, fragment, etc)

**Test Coverage:**
```python
# tests/unit/test_ast_nodes.py
- Create each node type
- Test node properties
- Test serialization (to_dict)
- Test visitor pattern
```

---

### 1.4 Parser (`parser/parser.py`)

**Deliverables:**
- [ ] EdenParser class
- [ ] 100+ parser tests
- [ ] Token stream → AST conversion

**Key Methods:**
- `parse(tokens)` → ASTNode
- `_parse_directive()` → ASTNode
- `_parse_expression()` → ExpressionNode
- `_parse_filter_chain()` → FilterNode

**Test Coverage:**
```python
# tests/unit/test_parser.py (100+ tests)
# For each directive family:
- Parse simple directive
- Parse directive with args
- Parse directive with body
- Parse nested directives
- Parse with expressions
- Parse invalid syntax → ParseError

# Specific form directive tests (20+ tests):
- Parse @csrf()
- Parse @render_field("name", {"options": "..."})
- Parse @checked(condition) { checked }
- Parse form field types
```

---

## Phase 1 Exit Criteria

Before moving to Phase 2, ensure:

- ✅ [x] Grammar spec complete and documented
- [ ] [ ] Tokenizer passes 80+ tests
- [ ] [ ] All AST node types defined
- [ ] [ ] Parser converts 100+ test templates to AST without errors
- [ ] [ ] Error messages point to correct line/column

### Success Metrics:
- **Grammar Coverage:** 100% of 40+ directives
- **Test Pass Rate:** 100% of 230+ tests (grammar + lexer + parser)
- **Error Reporting:** Line/column accurate for 95%+ of cases

---

## Testing Emphasis Throughout

### Per-Phase Testing Strategy:

**Phase 1 (Grammar/Parsing):**
- Unit tests: 230+ (grammar 50+, lexer 80+, parser 100+)
- Focus: Syntax validation, token accuracy, AST correctness

**Phase 2 (Code Generation/Runtime):**
- Unit tests: 500+ total
  - Form tests: 100+
  - Directive tests: 200+
  - Filter tests: 110+ (string, list, numeric, formatting)
  - Formatting tests: 70+ (phone, currency, intl formats)
- Integration tests: 40+ (basic end-to-end)
- Focus: Form field rendering, all directives, filters, intl formatting

**Phase 3 (Engine Integration):**
- Integration tests: 140+ (forms 40+, formatting 30+, real scenarios 20+)
- Focus: Engine API, caching, template loading

**Phase 4 (Optimization):**
- Performance tests: 70+ benchmarks (forms + filters included)
- Migration tests: 30+ Jinja2→EdenEngine conversion

**Phase 5 (Quality Assurance):**
- Security tests: 150+ (CSRF, injection, validation bypass)
- Edge cases: 100+ (unicode, deeply nested, circular deps, intl formats)
- Real-world: 30+ production templates (includes Ghana/Nigeria examples)

**Total Test Suite:** ~1,450+ tests by end of Phase 5

---

## Form Directives - Fully Integrated ✅

### Form Directives to Implement:

| Directive | Type | Phase | Tests |
|-----------|------|-------|-------|
| @csrf() | Token generation | 2 | 5 |
| @checked(cond) { checked } | Attribute helper | 2 | 10 |
| @selected(cond) { selected } | Attribute helper | 2 | 10 |
| @disabled(cond) { disabled } | Attribute helper | 2 | 5 |
| @readonly(cond) { readonly } | Attribute helper | 2 | 5 |
| @render_field(...) | Field renderer | 2 | 100 |
| @error("field") { } | Error display | 2 | 15 |

### Formatting Filters - fully Integrated ✅

| Filter | Purpose | Phase | Tests |
|--------|---------|-------|-------|
| currency(symbol, decimals?, locale?) | Currency formatting | 2 | 40+ |
| phone(format?, country?) | Phone formatting | 2 | 30+ |
| format(pattern) | Custom formatting | 2 | 5 |

**Supported Formatting Features:**
- Currency: $, €, £, ¥, ¢, ₹, ₱, ₩ + ISO codes (USD, EUR, GHS, etc)
- Phone: Ghana, Nigeria, USA, UK, France, Germany, Japan, China
- Locales: US, EU, Asia, Ghana, West Africa
- International formats with auto-detection

### Field Types in @render_field:

- text, email, tel, password, number, url, date, time
- textarea, select, checkbox, radio, file, hidden
- All with: label, required, placeholder, class, value, validation errors

### Form Test Files to Create:

```
tests/unit/test_forms.py (100+ tests)
├── Test each field type rendering
├── Test validation error display
├── Test @old() value population
├── Test CSRF token generation
├── Test attribute helpers
└── Test Accessibility features

tests/integration/test_forms_integration.py (40+ tests)
├── Multi-field forms
├── Nested forms with components
├── Dynamic field generation (@for loop)
├── Conditional field rendering (@if)
├── Form submission flows
└── Real-world user profile forms
```

---

## Project Structure Ready

```
eden_engine/
├── grammar/
│   ├── eden_directives.lark          ← Start here
│   └── grammar_tests.py
├── lexer/
│   ├── tokenizer.py
│   └── test_tokenizer.py
├── parser/
│   ├── ast_nodes.py
│   ├── parser.py
│   └── test_parser.py
├── [phases 2-5 structure prepared]
└── tests/
    ├── unit/
    │   ├── test_lexer.py
    │   ├── test_parser.py
    │   └── test_forms.py              ← Form testing
    ├── integration/
    │   └── test_forms_integration.py  ← Form scenarios
    ├── security/
    │   └── test_csrf_protection.py    ← CSRF testing
    └── fixtures/
        └── form_fixtures.py           ← Form test data
```

---

## Key Files & Locations

### Implementation Plan
📄 [EDEN_TEMPLATING_ENGINE_IMPLEMENTATION_PLAN.md](EDEN_TEMPLATING_ENGINE_IMPLEMENTATION_PLAN.md)
- All 5 phases detailed
- Updated with form directives
- Updated with 1,350+ test strategy

### Syntax Reference
📄 [EDEN_SYNTAX_STANDARD_FINAL.md](EDEN_SYNTAX_STANDARD_FINAL.md)
- All 40+ directives documented
- Form directives fully specified (with @render_field examples)
- One consistent pattern: `@directive(args) { body }`

### Examples
📄 [EDEN_TEMPLATING_ENGINE_EXAMPLES_OPTION_A.md](EDEN_TEMPLATING_ENGINE_EXAMPLES_OPTION_A.md)
- 9 real-world examples
- Example 9: Complete user profile form page
- All using consistent Option A syntax

### Quick Reference
📄 [EDEN_ENGINE_QUICK_REFERENCE.md](EDEN_ENGINE_QUICK_REFERENCE.md)
- Quick lookup for all directives
- 100-line cheat sheet

---

## Next Steps (Upon Phase 1 Completion)

1. **Phase 2 - Code Generation:** Implement CodeGenerator, expression evaluator, all 40+ directives, form rendering
2. **Comprehensive Form Testing:** 100+ unit tests + 40+ integration tests
3. **Phase 3 - Engine:** Template loader, caching, main API
4. **Phase 4 - Polish:** Performance optimization, migration tools, documentation
5. **Phase 5 - QA:** 1,350+ full test suite, security audit, production readiness

---

## Reference Metrics

| Metric | Value |
|--------|-------|
| Total Directives | 40+ |
| Form Directives | 7 |
| Field Types | 13 (text, email, textarea, select, checkbox, radio, etc) |
| Built-in Filters | 38+ |
| Formatting Filters (NEW) | 3 (currency, phone, format) |
| Supported Currencies | 30+ |
| Supported Phone Countries | 8+ (Ghana, Nigeria, USA, UK, France, Germany, Japan, China) |
| Test Cases (Phase 1) | 230+ |
| Test Cases (All Phases) | ~1,450+ |
| Implementation Time | 4-5 weeks |
| Phase 1 Duration | 1-1.5 weeks |
| Form Test Coverage | 140+ dedicated tests |
| Filter Test Coverage | 180+ dedicated tests (filters + formatting) |
| Target Coverage | > 95% lines, > 90% branches |

---

## Sign-Off

**Status:** ✅ READY TO KICKOFF PHASE 1

All planning complete. Design frozen. Ready to begin implementation.

Form directives fully integrated into planning. Comprehensive testing emphasized from start to finish.

**Proceed to Phase 1: Foundation & Parsing**
