# Eden Custom Templating Engine - Implementation Plan

**Status:** Detailed Specification (No Code Changes)  
**Target Timeline:** 4-5 weeks of focused development  
**Project Home:** `c:\ideas\eden\eden_engine/` (separate from main `eden/` package)  
**Objective:** Build production-ready templating engine with must-have features, all 40+ directives, HTML rendering, and external library support.

---

## 📋 Executive Summary

### **What We're Building**
A standalone, high-performance templating engine that:
- ✅ Compiles Eden @directive syntax to optimized Python bytecode
- ✅ Supports all 40+ existing Eden directives
- ✅ Adds must-have features: test functions, block inheritance, namespaced imports, type hints, safe mode
- ✅ Integrates with Jinja2 filters/escaping, uses Lark for parsing, simpleeval for expressions
- ✅ Maintains line-preserving error reporting
- ✅ Can be tested independently before merging into main Eden

### **Key Dependencies**
- **lark** — Grammar parsing (replaces manual tokenizer)
- **simpleeval** — Safe expression evaluation
- **markupsafe** — HTML escaping (from Jinja2)
- **Python 3.9+ ast module** — Code generation
- **Jinja2** — Filter system + escape utilities (optionally)

### **Project Structure**
```
eden_engine/                          # Root of new templating engine
├── grammar/
│   ├── eden_directives.lark         # Lark grammar definition
│   └── grammar_tests.py              # Grammar validation tests
├── lexer/
│   ├── tokenizer.py                  # Lexer implementation (Lark-based)
│   └── test_tokenizer.py
├── parser/
│   ├── ast_nodes.py                  # AST node definitions
│   ├── parser.py                     # AST builder from tokens
│   └── test_parser.py
├── compiler/
│   ├── codegen.py                    # AST → Python code generation
│   ├── optimizer.py                  # Bytecode optimization
│   └── test_codegen.py
├── runtime/
│   ├── context.py                    # Context/scope management
│   ├── evaluator.py                  # Expression evaluation
│   ├── filters.py                    # Built-in filters + registration
│   ├── tests.py                      # Test functions (is defined, is empty, etc)
│   ├── directives/
│   │   ├── __init__.py               # Directive registry
│   │   ├── control_flow.py           # @if, @for, @unless, etc
│   │   ├── components.py             # @component, @slot, @render_field
│   │   ├── inheritance.py            # @extends, @block, @yield
│   │   ├── forms.py                  # @csrf, @checked, @selected, @render_field
│   │   │                             # Field types: text, email, textarea, select,
│   │   │                             #             checkbox, radio, etc
│   │   ├── routing.py                # @url, @active_link
│   │   ├── auth.py                   # @auth, @guest, @htmx
│   │   ├── assets.py                 # @css, @js, @vite
│   │   ├── data.py                   # @let, @old, @json, @dump
│   │   └── messages.py               # @error, @messages
│   └── test_runtime.py
├── engine/
│   ├── template_engine.py            # Main EdenEngine class
│   ├── cache.py                      # Template caching + invalidation
│   ├── loader.py                     # Template file loader
│   └── test_engine.py
├── sandbox/
│   ├── safe_mode.py                  # Safe mode (restricted filters)
│   └── test_safe_mode.py
├── types/
│   ├── schemas.py                    # TypedDict schemas for contexts
│   ├── validator.py                  # Schema validation + type checking
│   └── test_types.py
├── scripts/
│   ├── benchmark.py                  # Performance profiling
│   ├── migration_tool.py             # Jinja2 → EdenEngine converter
│   └── playground.py                 # Interactive REPL
├── examples/
│   ├── basic.py                      # Simple usage example
│   ├── components.py                 # Component/slot example
│   ├── inheritance.py                # Block inheritance example
│   ├── type_hints.py                 # Type-safe templating
│   └── safe_mode.py                  # User-generated content
├── templates/
│   ├── example_base.html             # Example templates for testing
│   ├── example_component.html
│   └── example_page.html
├── docs/
│   ├── ARCHITECTURE.md               # Design doc
│   ├── DIRECTIVES_REFERENCE.md       # All 40+ directives
│   ├── GRAMMAR.md                    # PEG grammar explained
│   ├── MIGRATION_GUIDE.md            # Jinja2 → EdenEngine
│   └── API_REFERENCE.md              # Engine API
├── tests/
│   ├── test_integration.py           # End-to-end tests (50+ scenarios)
│   ├── test_directives.py            # All 40+ directives (250+ tests)
│   ├── test_forms.py                 # Form directives + field types (100+ tests)
│   ├── test_performance.py           # Speed + memory tests (30+ tests)
│   ├── test_edge_cases.py            # Corner cases (40+ tests)
│   ├── test_comprehensive.py         # Cross-feature integration (60+ tests)
│   └── fixtures/
│       ├── templates/
│       ├── form_fixtures.py
│       └── test_data.py
├── pyproject.toml                    # Package metadata
├── README.md                         # Quick start guide
└── IMPLEMENTATION_LOG.md             # Progress tracker (updated during dev)
```

---

## 🏗️ Phase Breakdown

### **PHASE 1: Foundation & Parsing (Weeks 1-1.5)**

**Deliverables:**
- ✅ Lark grammar fully defined
- ✅ Tokenizer working for all 40+ directives
- ✅ AST node classes complete
- ✅ Parser passes 100+ grammar test cases

**Components:**

#### **1.1 Grammar Definition** (`grammar/eden_directives.lark`)
```
SCOPE: Define complete PEG grammar for Eden syntax
- Control flow (@if, @unless, @for, @switch/@case)
- Components (@component, @slot, @render_field)
- Inheritance (@extends, @block, @yield, @section)
- Loops (@foreach variations, @empty)
- Loop helpers (@even, @odd, @first, @last)
- Authentication (@auth, @guest, @htmx, @non_htmx)
- Forms (@csrf, @checked, @selected, @disabled, @readonly)
  - Form field rendering: @render_field(name, options)
  - HTML attributes: @checked(), @selected(), @disabled(), @readonly()
  - Field-specific: text, email, tel, password, textarea, select, checkbox, radio
  - Form submission helpers
- Routing (@url, @active_link)
- Data helpers (@let, @old, @span, @json, @dump)
- Assets (@css, @js, @vite)
- Messages (@error, @messages)
- Special (@method, @fragment, @push/@stack)
- Expressions & variables ({{ }})
- Test functions (is defined, is empty, is odd, divisible_by, contains, etc)
- Filters (pipe-based chaining)

KEY RULES:
- Support both @directive() { } and @directive @if variations
- Nested block parsing (braces, not indentation)
- Expression parsing for conditions/loops
- Line/column tracking for error reporting
- Form options as dictionary arguments: @render_field("name", {"label": "...", "type": "..."})
```

**Deliverable Files:**
- `grammar/eden_directives.lark` — Complete grammar
- `grammar/grammar_tests.py` — 50+ test cases validating grammar

---

#### **1.2 Tokenizer** (`lexer/tokenizer.py`)
```
SCOPE: Wrap Lark into a clean tokenizer interface
- Load grammar from .lark file
- Tokenize template strings → token stream
- Track line/column for error reporting
- Preserve whitespace information (for output formatting)
- Support nested block detection

CLASS: EdenLexer
METHODS:
  tokenize(template_str: str) -> List[Token]
  get_line_number(pos: int) -> int
  get_column_number(pos: int) -> int
  
OUTPUT: Token objects with:
  - type (DIRECTIVE, TEXT, EXPR, LPAREN, RPAREN, etc)
  - value (string content)
  - line, column (for error reporting)
```

**Deliverable Files:**
- `lexer/tokenizer.py` — EdenLexer class
- `lexer/test_tokenizer.py` — 80+ tokenization tests

---

#### **1.3 AST Nodes** (`parser/ast_nodes.py`)
```
SCOPE: Define all AST node types (one per directive family + expressions)

BASE CLASS: ASTNode
  - Tracks line/column for error reporting
  - children: List[ASTNode]
  - accept(visitor) for visitor pattern

NODE TYPES (3+ for each category):

CONTROL FLOW:
  - IfNode(condition, body, else_body)
  - UnlessNode(condition, body, else_body)
  - ForNode(target, iterable, body, empty_body)
  - SwitchNode(expr, cases: List[CaseNode])
  - CaseNode(value, body)
  
COMPONENTS:
  - ComponentNode(name, slots: Dict[str, List[ASTNode]], attrs)
  - SlotNode(name, default_body)
  
INHERITANCE:
  - ExtendsNode(parent_path, body)
  - BlockNode(name, body)
  - YieldNode(name)
  - SectionNode(name, body)
  - PushNode(name, body)
  - SuperNode()
  
EXPRESSIONS & DATA:
  - ExpressionNode(ast.Expression)  # Wraps Python AST
  - FilterNode(value, filters: List[Filter])
  - TestNode(value, test_name, args)
  - LiteralNode(value)
  - IdentifierNode(name)
  - DotAccessNode(obj, attr)
  - CallNode(func, args)
  - ListNode(items)
  - DictNode(pairs)
  
SPECIAL:
  - BlockContentNode(content) — Raw HTML/text
  - DirectiveNode — Base for all directives

All nodes must support:
  - __repr__() for debugging
  - to_dict() for serialization
  - accept(visitor) for code generation
```

**Deliverable Files:**
- `parser/ast_nodes.py` — 40+ node types (~500 lines)
- `parser/test_ast_nodes.py` — Node construction tests

---

#### **1.4 Parser** (`parser/parser.py`)
```
SCOPE: Transform token stream → AST using Lark parse tree

CLASS: EdenParser
METHODS:
  parse(tokens: List[Token]) -> ASTNode (root)
  _parse_directive() -> ASTNode
  _parse_expression() -> ExpressionNode
  _parse_filter_chain() -> FilterNode
  _parse_test() -> TestNode

STRATEGY: Recursive descent or visitor pattern on Lark tree
- Convert Lark parse tree to AST nodes
- Validate directive nesting (can't nest @for in @if arbitrarily)
- Check for missing closing braces, mismatched directives
- Preserve line/column info from tokens

ERROR HANDLING:
- ParseError with line/column info
- Helpful messages ("Expected } to close @if block on line 5")
```

**Deliverable Files:**
- `parser/parser.py` — EdenParser class
- `parser/test_parser.py` — 100+ parse tests covering all directives

---

**Phase 1 Exit Criteria:**
- ✅ Grammar spec complete and documented
- ✅ Tokenizer passes 80+ tests
- ✅ All AST node types defined
- ✅ Parser converts 100+ test templates to AST without errors
- ✅ Error messages point to correct line/column

---

### **PHASE 2: Code Generation & Runtime (Weeks 2-2.5)**

**Deliverables:**
- ✅ AST → Python bytecode compiler working
- ✅ Expression evaluator (safe, handles all syntax)
- ✅ Context/scope management (no variable collisions)
- ✅ All 40+ directives implemented as runtime functions

**Components:**

#### **2.1 Code Generator** (`compiler/codegen.py`)
```
SCOPE: Convert AST → executable Python code

CLASS: CodeGenerator
METHODS:
  generate(ast_root: ASTNode) -> str  # Returns Python source code
  compile(ast_root: ASTNode) -> types.CodeType  # Returns bytecode
  
GENERATION STRATEGY:
- Emit Python function: def render_template(context, request=None, filters=None)
- Initialize output buffer: output = []
- Walk AST tree, emit Python statements for each node
- Each directive becomes either:
  a) if/for statement (control flow)
  b) function call (components, filters)
  c) method call (e.g., escaping)

EXAMPLE PSEUDOCODE:

INPUT AST:
  @if (user.active) {
    <p>{{ user.name | uppercase }}</p>
  } @else {
    <p>Not logged in</p>
  }

OUTPUT Python:
  ```python
  def render_template(context, request=None, filters=None):
      output = []
      if context.get('user', {}).get('active', False):
          output.append('<p>')
          output.append(escape(str(apply_filters(context['user']['name'], ['uppercase']))))
          output.append('</p>')
      else:
          output.append('<p>Not logged in</p>')
      return ''.join(output)
  ```

KEY OPTIMIZATIONS:
- Escape HTML at generation time where possible
- Pre-compile filter chains
- Flatten nested blocks to reduce function calls
- Use static strings directly (no escaping needed)

ERROR HANDLING:
- If AST node unknown, raise CompileError
- Type checking on generated code (compile() will catch syntax errors)
```

**Deliverable Files:**
- `compiler/codegen.py` — CodeGenerator class (~800 lines)
- `compiler/test_codegen.py` — 100+ codegen tests

---

#### **2.2 Expression Evaluator** (`runtime/evaluator.py`)
```
SCOPE: Evaluate {{ expressions }} safely without eval()

CLASS: ExpressionEvaluator
METHODS:
  evaluate(expr_node: ExpressionNode, context: Dict) -> Any
  safe_getattr(obj, attr) -> Any
  apply_filters(value, filter_names: List[str], args: List) -> Any
  apply_test(value, test_name: str, args: List) -> bool

EXPRESSION SUPPORT:
- Variables: {{ user }}
- Dotted access: {{ user.profile.name }}
- Array indexing: {{ items[0] }}
- Method calls: {{ user.get_display_name() }}
- Filter chaining: {{ name | uppercase | truncate(20) }}
- Test functions: @if (count is odd) { }
- Arithmetic: {{ count + 1 }}
- Comparisons: {{ age > 18 }}
- Logical ops: @if (user.active && user.verified) { }
- Ternary: {{ "Admin" if user.is_admin else "User" }}

SAFETY FEATURES:
- No __dunder__ attribute access
- No exec/eval calls
- Whitelist allowed methods (get, upper, lower, etc)
- Rate-limit expensive operations (deep recursion)

IMPLEMENTATION:
- Use simpleeval for base expression parsing
- Extend with custom functions for tests
- Cache compiled expressions for performance

FILTER SYSTEM:
- Pre-register filters: uppercase, lowercase, truncate, join, etc
- Allow custom filter registration
- Filters are chainable: value | f1 | f2(arg) | f3

BUILT-IN FILTERS (20+):
1. uppercase — Convert to uppercase: {{ name | uppercase }}
2. lowercase — Convert to lowercase: {{ name | lowercase }}
3. capitalize — Capitalize first letter: {{ name | capitalize }}
4. title — Title case: {{ "hello world" | title }} → "Hello World"
5. reverse — Reverse string/list: {{ "abc" | reverse }}
6. length — Get length: {{ items | length }}
7. join(sep) — Join list with separator: {{ tags | join(", ") }}
8. split(sep) — Split string into list: {{ "a,b,c" | split(",") }}
9. slice(start, end) — Slice string/list: {{ text | slice(0, 10) }}
10. truncate(len, suffix) — Truncate with ellipsis: {{ text | truncate(20, "...") }}
11. trim — Strip whitespace: {{ text | trim }}
12. ltrim — Left trim: {{ text | ltrim }}
13. rtrim — Right trim: {{ text | rtrim }}
14. round(decimals) — Round number: {{ price | round(2) }}
15. abs — Absolute value: {{ num | abs }}
16. default(value) — Provide default: {{ missing_var | default("N/A") }}
17. first — First element: {{ items | first }}
18. last — Last element: {{ items | last }}
19. nth(index) — Get nth element: {{ items | nth(2) }}
20. sort — Sort list: {{ items | sort }}
21. reverse_sort — Reverse sort: {{ items | reverse_sort }}
22. unique — Unique items: {{ tags | unique }}
23. min — Minimum value: {{ numbers | min }}
24. max — Maximum value: {{ numbers | max }}
25. sum — Sum values: {{ numbers | sum }}
26. avg — Average: {{ numbers | avg }}
27. map(attr) — Map attribute: {{ users | map("name") | join(", ") }}
28. select(attr, value) — Filter by attribute: {{ users | select("is_active") }}
29. reject(attr, value) — Reject by attribute: {{ users | reject("is_banned") }}
30. format(pattern) — String formatting: {{ num | format("${:,.2f}") }}
31. json — JSON encode: {{ data | json }}
32. escape — HTML escape: {{ html_string | escape }}
33. safe — Mark as safe HTML: {{ rendered_html | safe }}
34. slugify — Convert to URL slug: {{ "Hello World" | slugify }} → "hello-world"
35. pluralize(singular, plural) — Pluralize: {{ count | pluralize("item", "items") }}
36. conditional(true_val, false_val) — Ternary in filter: {{ active | conditional("Yes", "No") }}
37. currency(symbol, decimals?, locale?) — Currency formatting: {{ 1234.56 | currency("¢", 2) }} → "¢1,234.56"
38. phone(format?, country?) — Phone number formatting: {{ "0248160391" | phone("GH") }} → "+233 248 160 391"

SUPPORTED CURRENCY SYMBOLS:
- $, €, £, ¥, ₹, ₽, ₩, ¢, ₱, ₿
- ISO codes: USD, EUR, GHS, PHP, INR, JPY, CNY, NGN, etc
- Automatic rounding to 2 decimals

SUPPORTED PHONE COUNTRIES:
- Ghana (GH), Nigeria (NG), USA (US), UK, France (FR), Germany (DE), Japan (JP), China (CN)
- Auto-detection and formatting for country codes
- International and standard format options

FILTER REGISTRATION:
- Users can register custom filters via engine API
- engine.register_filter("my_filter", my_filter_func)
- Filters must be pure functions (no side effects)
- Filters should handle None gracefully
- Chaining automatically passes output to next filter
```

**Deliverable Files:**
- `runtime/evaluator.py` — ExpressionEvaluator class
- `runtime/filters.py` — Built-in filters + registration API
- `runtime/tests.py` — Test functions (is defined, is empty, is odd, etc)
- `runtime/test_evaluator.py` — 150+ expression tests

---

#### **2.3 Context & Scope Management** (`runtime/context.py`)
```
SCOPE: Manage variable scoping for @for loops, components, @let

CLASS: RenderContext
METHODS:
  push(scope_dict) -> ContextManager  # Enter nested scope
  pop()  # Exit scope
  set(key, value)  # Set in current scope
  get(key, default=None)  # Search up scope chain
  update(dict)  # Merge into current scope

SCOPE CHAIN:
- Global scope (user context)
- For loop scope (includes 'loop' variable with metadata)
- Component scope (isolated from parent)
- Let assignment scope (within block)

SPECIAL VARIABLES:
- loop.index (0-based)
- loop.index1 (1-based)
- loop.first / loop.last
- loop.length
- loop.even / loop.odd
- {{ slot_name }} (in components)

IMPLEMENTATION:
- Stack of dicts for scope chain
- __missing__ handler for get() to walk stack
- Context manager for push/pop
```

**Deliverable Files:**
- `runtime/context.py` — RenderContext class
- `runtime/test_context.py` — Scope tests

---

#### **2.4 Directive Runtime Implementations** (`runtime/directives/`)
```
SCOPE: Implement handler functions for each directive family

FILE STRUCTURE:
  directives/__init__.py  — DirectiveRegistry + directive decorators
  directives/control_flow.py  — @if, @unless, @for, @switch
  directives/components.py    — @component, @slot, @render_field
  directives/inheritance.py   — @extends, @block, @yield, @section, @push
  directives/forms.py         — @csrf, @checked, @selected, @disabled
  directives/routing.py       — @url, @active_link
  directives/auth.py          — @auth, @guest, @htmx, @non_htmx
  directives/assets.py        — @css, @js, @vite
  directives/data.py          — @let, @old, @json, @dump, @span
  directives/messages.py      — @error, @messages

PATTERN FOR EACH DIRECTIVE:

@directive_registry.register("csrf")
def csrf_handler(context: RenderContext, request) -> str:
    token = context.get('csrf_token') or request.session.get('csrf_token')
    return f'<input type="hidden" name="csrf_token" value="{escape(token)}">'

@directive_registry.register("auth")
def auth_handler(context: RenderContext) -> bool:
    return context.get('user') and context['user'].get('is_authenticated', False)

@directive_registry.register("for")
def for_handler(target: str, iterable: Any, body_fn, empty_fn=None):
    results = []
    items = list(iterable) if iterable else []
    
    if not items and empty_fn:
        return empty_fn()
    
    for i, item in enumerate(items):
        loop_vars = {
            'index': i,
            'index1': i + 1,
            'first': i == 0,
            'last': i == len(items) - 1,
            'even': i % 2 == 0,
            'odd': i % 2 == 1,
            'length': len(items),
            target: item
        }
        results.append(body_fn(loop_vars))
    
    return ''.join(results)

Each directive returns one of:
- str (HTML output)
- bool (condition result, used by codegen)
- callable (body function passed in)
```

**Deliverable Files:**
- `runtime/directives/` — 10 files implementing all 40+ directives
- `runtime/test_directives.py` — Test each directive in isolation
- `runtime/directives/__init__.py` — DirectiveRegistry class

---

**Phase 2 Exit Criteria:**
- ✅ CodeGenerator produces valid Python code for all AST node types
- ✅ All 40+ directives have working runtime implementations
- ✅ All form directives fully implemented (@csrf, @checked, @render_field, etc)
- ✅ @render_field supports all field types (text, email, textarea, select, checkbox, radio)
- ✅ Expression evaluator handles variables, filters, tests safely
- ✅ Context management prevents variable collisions in loops/components
- ✅ 250+ unit tests passing (including 100+ form tests)
- ✅ All form field types tested with valid/invalid data

---

### **PHASE 3: Engine Integration & Features (Weeks 3-3.5)**

**Deliverables:**
- ✅ Main EdenEngine class (compile, render, cache)
- ✅ Template loader (file I/O + path resolution)
- ✅ Caching system (LRU + mtime checking)
- ✅ Must-have features (test functions, block inheritance, namespaced imports, type hints, safe mode)

**Components:**

#### **3.1 Template Engine** (`engine/template_engine.py`)
```
SCOPE: Main API for compiling and rendering templates

CLASS: EdenEngine
PROPERTIES:
  - template_dir: str
  - cache_size: int
  - debug: bool
  - auto_reload: bool
  - enable_type_checking: bool

METHODS:

  compile(source: str) -> CompiledTemplate
    - Lexes → Parses → Generates → Compiles Python code
    - Returns callable(context) function
    - Caches compiled bytecode
    - On error: raises CompileError with line/column

  render(path: str, context: Dict) -> str
    - Loads template file
    - Compiles if not cached
    - Executes with context
    - Returns HTML string
    - On error: raises RenderError with source line

  render_string(source: str, context: Dict) -> str
    - Like render() but with string source (no file lookup)

  register_filter(name: str, func: Callable) -> None
    - Add custom filter to all templates

  register_test(name: str, func: Callable) -> None
    - Add custom test function to all templates

  register_directive(name: str, handler: Callable) -> None
    - Add custom directive

  set_context_schema(cls: Type[TypedDict]) -> None
    - Enable type checking for context dict

INTERNAL METHODS:
  _load_template(path: str) -> str
  _compile_and_cache(source: str, cache_key: str) -> CompiledTemplate
  _invalidate_cache(path: str) -> None

USAGE EXAMPLE:

engine = EdenEngine(template_dir='templates/')
html = engine.render('home.html', {
    'user': user_obj,
    'posts': posts_list
})
```

**Deliverable Files:**
- `engine/template_engine.py` — EdenEngine class
- `engine/test_engine.py` — Engine integration tests

---

#### **3.2 Template Caching** (`engine/cache.py`)
```
SCOPE: Cache compiled templates + track file changes

CLASS: TemplateCache (LRU)
PROPERTIES:
  - max_size: int
  - ttl: int (seconds, optional)

METHODS:
  get(key: str) -> Optional[CompiledTemplate]
  set(key: str, value: CompiledTemplate) -> None
  invalidate(key: str) -> None
  clear() -> None
  
CACHE ENTRY:
  {
    'source': original template string (for validation),
    'compiled_fn': callable render function,
    'bytecode': pickle of bytecode,
    'mtime': file modification time,
    'created_at': timestamp,
    'hits': count of times used
  }

INVALIDATION LOGIC:
- On each render: check if file mtime changed
- If changed: recompile and update cache
- If auto_reload=False: only check on startup
- If auto_reload=True: always check (dev mode)

PERFORMANCE:
- LRU eviction when cache full
- ~0.5ms lookup time
- Memory: ~50KB per cached template (typical)
```

**Deliverable Files:**
- `engine/cache.py` — TemplateCache class
- `engine/test_cache.py` — Cache behavior tests

---

#### **3.3 Template Loader** (`engine/loader.py`)
```
SCOPE: Load templates from filesystem + resolve paths

CLASS: TemplateLoader
METHODS:
  load(path: str) -> str
  exists(path: str) -> bool
  get_sources(path: str) -> Tuple[str, str, Callable]  # For Jinja2 compat
  
PATH RESOLUTION:
- Absolute paths: template_dir / path
- Prevent directory traversal: raise SecurityError on ../../../etc/passwd
- Support nested: templates/layouts/base.html
- Support namespaced: @import "components/card" as card

SEARCH PATHS (in order):
1. template_dir / path
2. template_dir / path.html
3. template_dir / includes / path
4. template_dir / includes / path.html

FILE ENCODING:
- Always UTF-8
- Preserve BOM detection
```

**Deliverable Files:**
- `engine/loader.py` — TemplateLoader class
- `engine/test_loader.py` — Loader tests

---

#### **3.4 Must-Have Feature: Test Functions** (`runtime/tests.py`)
```
SCOPE: Implement "is X" test functions from Tera

BUILT-IN TESTS:

  @if (user.email is defined) { ... }     — Not None/null
  @if (items is empty) { ... }             — len(items) == 0
  @if (count is odd) { ... }               — count % 2 == 1
  @if (count is even) { ... }              — count % 2 == 0
  @if (count is divisible_by(3)) { ... }   — count % 3 == 0
  @if (type is string) { ... }             — isinstance(val, str)
  @if (type is number) { ... }             — isinstance(val, (int, float))
  @if (type is dict) { ... }               — isinstance(val, dict)
  @if (type is list) { ... }               — isinstance(val, list)

IMPLEMENTATION:
- Add TestFunctionRegistry
- Register built-in tests in evaluator
- Codegen emits: apply_test(value, 'defined') → bool
- Runtime: lookup 'defined' in registry, call it

SYNTAX SUPPORT:
  @if (var is defined) { }           — Single arg (the value)
  @if (count is divisible_by(5)) { } — Function call with args
  @if (val is not defined) { }       — Negation with "not"
```

**Deliverable Files:**
- `runtime/tests.py` — Built-in test functions
- `runtime/test_tests.py` — Test function tests

---

#### **3.5 Must-Have Feature: Block Inheritance** (`runtime/directives/inheritance.py`)
```
SCOPE: Enhance @extends/@block/@yield for cleaner inheritance

IMPROVEMENTS OVER JINJA2:
- @block name { } instead of {% block name %}...{% endblock %}
- @section name { } as alias for @block
- @super to include parent block content
- Block overrides in child can use @super { parent content }
- Named yielding: @yield "header" (renders block "header")

EXAMPLE:

BASE TEMPLATE (layouts/base.html):
  <!DOCTYPE html>
  <html>
    <head>
      @block head {
        <title>My Site</title>
      }
    </head>
    <body>
      @block content { }
      @block footer {
        <footer>© 2025</footer>
      }
    </body>
  </html>

CHILD TEMPLATE (pages/home.html):
  @extends "layouts/base"
  
  @block head {
    <title>Home - My Site</title>
    @super { }  <!-- append to parent head -->
  }
  
  @block content {
    <h1>Welcome</h1>
    <p>This is the home page.</p>
  }

IMPLEMENTATION:
- Parse @extends path at top of file
- Identify all @block definitions in current template
- Load parent template, parse it
- Recursively resolve parent blocks
- Merge child blocks into parent's block hierarchy
- Render final merged template

AT CODEGEN:
- Store block definitions in namespace
- When @yield encountered, lookup block definition
- Emit function call: yield_block(block_namespace, block_name)
- If block not defined, use parent's default
```

**Deliverable Files:**
- `runtime/directives/inheritance.py` — Update @extends/@block/@yield
- Tests included in `runtime/test_directives.py`

---

#### **3.6 Must-Have Feature: Namespaced Imports** (`compiler/namespaces.py`)
```
SCOPE: Add import system to prevent name collisions

SYNTAX:

  @import "components/cards" as card
  @import "helpers/text" as text
  
  @component(card.button, label="Click") { }
  {{ text.truncate(heading, 20) }}

IMPLEMENTATION:
- Parse @import statements at template start
- Build namespace map: {"card": {...}, "text": {...}}
- Codegen: qualify function calls with namespace
- Runtime: lookup resolved function in namespace

NAMESPACE RESOLUTION:
- @import "components/cards" loads templates/components/cards.html
- Scans for @macro/@component/@function definitions
- Builds namespace dict from those definitions

EXAMPLE COMPONENT FILE (components/cards.html):

  @macro card(title, shadow="md") {
    <div class="card shadow-{{ shadow }}">
      {{ title }}
      @slot content { }
    </div>
  }
  
  @macro button(label, type="primary") {
    <button class="btn-{{ type }}">{{ label }}</button>
  }

Then imported as:
  @import "components/cards" as card
  
  @card.card(title="My Card") { ... }
  @card.button(label="Save") { }
```

**Deliverable Files:**
- `compiler/namespaces.py` — Namespace resolution
- Update `parser/parser.py` to handle @import
- Update `compiler/codegen.py` to emit namespace lookups

---

#### **3.7 Must-Have Feature: Type Hints in Context** (`types/schemas.py`)
```
SCOPE: Enable IDE autocomplete + type validation

USAGE:

  from typing import TypedDict, Optional
  from eden.types import ContextSchema
  
  class UserContext(TypedDict):
      name: str
      email: str
      age: int
      is_admin: bool
  
  class PageContext(TypedDict):
      user: UserContext
      posts: List[Dict]
      page_title: str
  
  engine = EdenEngine(template_dir='templates/')
  engine.set_context_schema(PageContext)
  
  html = engine.render('home.html', {
      'user': user_obj,
      'posts': posts,
      'page_title': 'Home'
  })

IMPLEMENTATION:
- At engine.render() time, validate context dict against schema
- If key missing or type wrong, raise ValidationError with helpful message
- At codegen time, emit type hints in generated Python code:
  ```python
  def render_template(context: PageContext, ...) -> str:
  ```
- IDE plugin can now autocomplete context.user.name

TYPE CHECKING:
- Use typeguard for runtime validation
- Optional: mypy plugin to check template types at static analysis time
- Emit warnings if context doesn't match schema (debug mode)

ERROR MESSAGES:
  "Context validation failed: 'user.email' must be str, got NoneType"
  "Context validation failed: 'posts' is required but missing"
```

**Deliverable Files:**
- `types/schemas.py` — TypedDict utilities
- `types/validator.py` — Runtime validation
- Update `engine/template_engine.py` to validate

---

#### **3.8 Must-Have Feature: Safe Mode** (`sandbox/safe_mode.py`)
```
SCOPE: Restricted execution for user-generated templates

USE CASE:
- User-generated newsletter templates
- CMS content with limited directives
- Untrusted third-party templates
- Sandboxed component libraries

SAFE MODE CONFIG:

  engine = EdenEngine(template_dir='templates/')
  safe_config = {
      'allowed_directives': ['if', 'for', 'component'],
      'allowed_filters': ['uppercase', 'lowercase', 'truncate'],
      'allowed_attributes': ['name', 'email', 'age'],  # Whitelist
      'max_output_size': 1_000_000,  # 1MB limit
      'max_execution_time': 5,  # 5 second timeout
      'no_method_calls': True,  # No .method() access
  }
  
  html = engine.render_safe('user_template.html', context, safe_config)

ENFORCEMENT:
- Lexer: reject unknown directives
- Evaluator: reject attribute access not in whitelist
- Evaluator: reject method calls (obj.method())
- Codegen: wrap render function in timeout + size limit
- Runtime: enforce allowed_filters list

ALLOWED OPERATIONS IN SAFE MODE:
  {{ variable }}
  {{ variable | filter }}
  {{ variable | filter1 | filter2 }}
  @if (condition) { ... }
  @for (item in items) { ... }
  @component("card", data) { }

FORBIDDEN IN SAFE MODE:
  {{ obj.method() }}      — Method calls
  {{ obj.private }}       — Access not in whitelist
  @let x = ...           — Variable assignment
  @import ...            — Imports
  @extends ...           — Inheritance
```

**Deliverable Files:**
- `sandbox/safe_mode.py` — SafeModeConfig + enforcement
- `sandbox/test_safe_mode.py` — Security tests

---

**Phase 3 Exit Criteria:**
- ✅ EdenEngine class fully functional
- ✅ Caching works (mtime checking, auto-reload)
- ✅ Template loader handles paths + namespaces
- ✅ Test functions working (@if var is defined)
- ✅ Block inheritance working (@extends, @block, @super)
- ✅ Namespaced imports working (@import ... as ...)
- ✅ Type validation working (context schemas)
- ✅ Safe mode enforces restrictions
- ✅ 300+ integration tests passing

---

### **PHASE 4: Optimization & Polish (Weeks 4-4.5)**

**Deliverables:**
- ✅ Performance benchmarks (render time, memory)
- ✅ Edge case handling + error messages
- ✅ Documentation complete
- ✅ Examples + migration guide
- ✅ Internal playground/REPL for testing

**Components:**

#### **4.1 Performance Optimization** (`compiler/optimizer.py`)
```
SCOPE: Optimize generated code for speed

STRATEGIES:
1. Pre-compile filter chains to avoid runtime lookups
2. Inline small templates to eliminate function call overhead
3. Move constant expressions outside loops
4. Use compiled regexes for repeated patterns

EXAMPLE BEFORE (Naive):
  output.append(apply_filter(apply_filter(name, 'upper'), 'trunc', 20))

AFTER (Optimized):
  # Pre-compiled filter chain at generation time
  filter_chain = [upper_filter, lambda x: truncate_filter(x, 20)]
  output.append(apply_filters(name, filter_chain))

PROFILING:
- Measure render time for 100+ template scenarios
- Memory usage per template instance
- CPU time in lexer vs parser vs codegen vs runtime
- Cache hit rates in typical workloads

TARGETS:
- Simple template: < 1ms
- Complex template: < 10ms
- Memory per template: < 100KB
```

**Deliverable Files:**
- `compiler/optimizer.py` — Optimization passes
- `scripts/benchmark.py` — Performance testing

---

#### **4.2 Error Handling & Messages** (Throughout)
```
SCOPE: Ensure all errors point to source lines with context

CUSTOM EXCEPTION TYPES:

  EdenError (base)
    ├─ SyntaxError (lexer/parser)
    ├─ CompileError (codegen)
    ├─ RenderError (runtime)
    ├─ ValidationError (type checking)
    └─ SecurityError (safe mode violation)

ERROR MESSAGE FORMAT:

  Template Error in pages/home.html:
    Line 15: @for (post in unknown_var) {
                              ^
    NameError: 'unknown_var' is not defined
    Did you mean: 'posts'?
    
    Available variables: user, posts, page_title

  Context (lines 12-18):
    12 | @block content {
    13 |     <div class="posts">
    14 |         @if (posts) {
    15 |             @for (post in unknown_var) {  <-- Error here
    16 |                 <article>{{ post.title }}</article>
    17 |             }
    18 |         }

IMPLEMENTATION:
- Preserve line/column in all AST nodes
- At render error: catch exception, add context + suggestions
- Use difflib for "Did you mean?" suggestions
```

**Deliverable Files:**
- `engine/exceptions.py` — Custom exception types
- Integration into all components (lexer, parser, codegen, runtime)

---

#### **4.3 Documentation** (`docs/`)
```
DELIVERABLES:

1. ARCHITECTURE.md (5 pages)
   - How the engine works overall
   - Data flow: template → lexer → parser → codegen → runtime
   - Design decisions + tradeoffs

2. DIRECTIVES_REFERENCE.md (10 pages)
   - Complete reference for all 40+ directives
   - Syntax examples for each
   - Common pitfalls

3. GRAMMAR.md (3 pages)
   - Lark grammar syntax explained
   - How to extend with custom directives

4. API_REFERENCE.md (5 pages)
   - EdenEngine API
   - Using filters, tests, directives
   - Type validation API

5. MIGRATION_GUIDE.md (3 pages)
   - Jinja2 → EdenEngine migration
   - Differences + gotchas
   - Automated converter tool

6. Performance.md (2 pages)
   - Benchmark results
   - Caching strategies
   - Optimization tips
```

**Deliverable Files:**
- All docs/ files (~30 pages)

---

#### **4.4 Examples** (`examples/`)
```
DELIVERABLES:

1. basic.py
   - Simple "Hello {{ name }}" example
   - Context dict usage
   
2. components.py
   - Define reusable components
   - With slots
   - Nested components

3. inheritance.py
   - Base layout
   - Child page with @extends
   - @block overrides

4. type_hints.py
   - TypedDict context schema
   - IDE autocomplete
   - Validation errors

5. safe_mode.py
   - User-generated templates
   - Restricted directive list
   - Whitelist of allowed attributes

6. playground.py
   - Interactive REPL
   - Load template, render with live context
   - Test syntax in real-time
```

**Deliverable Files:**
- 6 example files + templates

---

#### **4.5 Migration Tool** (`scripts/migration_tool.py`)
```
SCOPE: Auto-convert Jinja2 templates to Eden syntax

CONVERSIONS:

  Jinja2                          Eden
  {% if x %}                      @if (x) {
  {% endif %}                     }
  {% for item in items %}         @for (item in items) {
  {% endfor %}                    }
  {% block name %}...{% endblock %} @block name { ... }
  {% extends "base" %}            @extends "base"
  {% include "partial" %}         @include "partial"
  {{ var | upper }}               {{ var | uppercase }}  (filter name updates)
  {# comment #}                   <!-- Eden uses HTML comments --> (with @ prefix if directive)

USAGE:

  python scripts/migration_tool.py --source old_templates/ --output new_templates/
  
  # Outputs:
  # - Converted templates
  # - Report of manual fixes needed
  # - Warnings for unsupported syntax

LIMITATIONS:
- Won't convert custom Jinja2 extensions (requires manual work)
- Custom filters need registration in new engine
- Test operators may differ
```

**Deliverable Files:**
- `scripts/migration_tool.py` — Conversion script

---

**Phase 4 Exit Criteria:**
- ✅ All templates render in < 10ms (benchmarked)
- ✅ Memory usage < 100KB per template
- ✅ Error messages include context + suggestions
- ✅ All documentation complete (30 pages)
- ✅ 6+ examples cover all major use cases
- ✅ Migration tool converts 95%+ of Jinja2 syntax
- ✅ Playground REPL works smoothly

---

### **PHASE 5: Testing & Deployment (Weeks 5)**

**Deliverables:**
- ✅ 500+ test cases covering all features
- ✅ Performance regression tests
- ✅ Security audit (safe mode)
- ✅ Ready for production merger into Eden

**Components:**

#### **5.1 Comprehensive Test Suite Structure**
```
STRUCTURE:

tests/
├── unit/
│   ├── test_lexer.py (80+ tests — tokenization for all directives)
│   ├── test_parser.py (100+ tests — AST generation)
│   ├── test_codegen.py (100+ tests — Python code generation)
│   ├── test_evaluator.py (150+ tests — expression evaluation, filters, tests)
│   ├── test_directives.py (200+ tests — all 40+ directives in isolation)
│   ├── test_forms.py (100+ tests — COMPREHENSIVE FORM TESTING)
│   │   └── Test each field type: text, email, textarea, select, checkbox, radio
│   │   └── Test validation error rendering
│   │   └── Test @old() value population
│   │   └── Test CSRF token generation
│   │   └── Test attribute conditional rendering
│   ├── test_cache.py (30+ tests)
│   └── test_filters.py (50+ tests — all 20+ built-in filters)
│
├── integration/
│   ├── test_end_to_end.py (60+ e2e scenarios)
│   ├── test_inheritance.py (30+ block inheritance cases)
│   ├── test_components.py (40+ component scenarios)
│   ├── test_namespacing.py (20+ import/namespace cases)
│   ├── test_forms_integration.py (40+ FORM INTEGRATION TESTS)
│   │   └── Multi-field forms
│   │   └── Nested forms with components
│   │   └── Dynamic field generation with @for
│   │   └── Conditional field rendering
│   ├── test_mixed_directives.py (30+ tests using 3+ directives per test)
│   └── test_real_world_templates.py (20+ production-like scenarios)
│
├── performance/
│   ├── test_render_speed.py (perf regression tests)
│   ├── test_memory_usage.py (memory profiling)
│   ├── test_cache_efficiency.py (30+ cache benchmarks)
│   └── test_form_render_performance.py (form field rendering benchmarks)
│
├── security/
│   ├── test_safe_mode.py (50+ sandbox tests)
│   ├── test_injection_prevention.py (SQL/XSS/template injection)
│   ├── test_attribute_whitelist.py (allowed HTML attributes)
│   ├── test_csrf_protection.py (CSRF token validation)
│   └── test_form_validation_bypass.py (prevent validation bypass)
│
├── edge_cases/
│   ├── test_unicode.py (📝 emoji, RTL text, multi-byte chars)
│   ├── test_deeply_nested.py (stress testing deep nesting)
│   ├── test_circular_dependencies.py (component circular refs)
│   ├── test_error_handling.py (error reporting + line numbers)
│   ├── test_large_context.py (1000+ variable contexts)
│   └── test_malformed_templates.py (invalid syntax recovery)
│
└── fixtures/
    ├── templates/ (test template files)
    ├── test_data.py (sample contexts with users, forms, etc)
    ├── form_fixtures.py (form definitions + validation rules)
    └── real_world/ (production templates from Eden)

TEST COVERAGE TARGET:
- Line coverage: > 95%
- Branch coverage: > 90%
- All 40+ directives: 100% coverage
- All 20+ built-in filters: 100% coverage
- Form directives: 100% with multiple field types
- Error paths: 100% coverage
```

**Coverage Areas (Comprehensive):**

| Area | # Tests | Priority | Special Notes |
|------|---------|----------|---------------|
| Directive Syntax (40+ directives) | 200 | ⭐⭐⭐⭐⭐ | Each directive: valid + invalid args |
| Expression Evaluation | 150 | ⭐⭐⭐⭐⭐ | Variables, filters, tests, operators |
| Component/Slots | 80 | ⭐⭐⭐⭐ | Named slots, fallbacks, composition |
| Block Inheritance | 60 | ⭐⭐⭐⭐ | Multi-level, @super, complex layouts |
| Form Directives | 150 | ⭐⭐⭐⭐⭐ | **NEW**: All field types + validation |
| Error Handling | 100 | ⭐⭐⭐⭐ | Line numbers, helpful messages |
| Safe Mode | 70 | ⭐⭐⭐⭐ | Sandbox restrictions + bypasses |
| Filters (20+ filters) | 80 | ⭐⭐⭐⭐ | Each filter: various input types |
| Formatting (phone, currency) | 70 | ⭐⭐⭐⭐⭐ | **NEW**: Intl formats + locales |
| Test Functions | 40 | ⭐⭐⭐ | is defined, is empty, is odd, etc |
| Type Validation | 40 | ⭐⭐⭐ | TypedDict schemas |
| Integration Scenarios | 100 | ⭐⭐⭐⭐⭐ | Real-world multi-directive combos |
| Performance | 50 | ⭐⭐⭐ | Regression tests, benchmarks |
| Unicode/i18n | 30 | ⭐⭐ | Emoji, RTL, multi-byte |
| Edge Cases | 60 | ⭐⭐⭐ | Circular refs, deep nesting, etc |
| Security | 100 | ⭐⭐⭐⭐⭐ | Injection, CSRF, validation bypass |
| **Total** | **~1,350** | | **3x more than initial plan** |

---

#### **5.2 Comprehensive Test Execution Strategy**
```
CONTINUOUS TESTING:

1. UNIT TESTS (400+ tests)
   pytest tests/unit/
   - Fast: < 10 seconds
   - Run on every commit
   - 80/20 rule: catch most bugs quickly
   - Include: test_forms.py (100+ form-specific tests)

2. INTEGRATION TESTS (200+ tests)
   pytest tests/integration/
   - Medium: 60 seconds
   - Run on main branch before merge
   - Include: test_forms_integration.py (40+ form scenarios)
   - Verify features work together
   - Test real composites: forms + @for loops, forms + @if, etc

3. EDGE CASE TESTS (150+ tests)
   pytest tests/edge_cases/
   - Medium: 40 seconds
   - Run before release
   - Cover malformed input, extreme nesting, etc

4. FORM-SPECIFIC TESTS (140+ tests) [NEW]
   pytest tests/unit/test_forms.py tests/integration/test_forms_integration.py
   - Field type coverage: text, email, tel, textarea, select, checkbox, radio
   - Validation: @error rendering, @old value population
   - Attributes: @checked, @selected, @disabled, @readonly
   - CSRF: token generation and validation
   - Form composition: multi-field forms, nested components
   - Accessibility: labels, ARIA attributes

5. PERFORMANCE TESTS (50+ benchmarks)
   pytest tests/performance/ --benchmark
   - Slow: 3 minutes (includes form benchmarks)
   - Run nightly on main
   - Alert if render time increases > 10%
   - Include form_render_performance: measure field rendering speed

6. SECURITY TESTS (150+ tests)
   pytest tests/security/ --strict
   - Slow: 2 minutes
   - Run before release
   - Non-negotiable: must pass 100%
   - Include test_csrf_protection.py: CSRF token validation
   - Include test_form_validation_bypass.py: prevent client-side bypass

PYTEST CONFIGURATION:
- pytest.ini with test discovery rules
- conftest.py with shared fixtures
- markers: @pytest.mark.slow, @pytest.mark.security, @pytest.mark.forms
- Coverage reporting: --cov=eden_engine --cov-report=html

CI/CD PIPELINE:
- Pre-commit: unit + form tests (< 15 seconds)
- PR checks: all unit + integration + form tests
- Push to main: all tests + security + performance
- Nightly: full suite on multiple Python versions (3.9-3.13)
```

**Deliverable Files:**
- Complete test suite (500+ tests)
- pytest.ini + conftest.py

---

#### **5.3 Docker / Deployment Checklist**
```
BEFORE MERGING INTO EDEN:

Code Quality:
  ☐ Black formatting passes
  ☐ Flake8 linting passes
  ☐ mypy type checking passes
  ☐ No hardcoded paths or credentials

Documentation:
  ☐ All public APIs documented
  ☐ 6+ examples provided
  ☐ README complete
  ☐ API reference complete
  ☐ Migration guide complete

Testing:
  ☐ 500+ tests passing
  ☐ Coverage > 95%
  ☐ Performance baselines established
  ☐ Security audit passed

Integration:
  ☐ Works with existing Eden routes
  ☐ Compatible with current ORM
  ☐ CSRF tokens work
  ☐ Auth middleware works
  ☐ No breaking changes to old Jinja2 wrappers

Release:
  ☐ CHANGELOG updated
  ☐ Version bumped (semantic versioning)
  ☐ Package published to PyPI (if standalone)
  ☐ Docs published to site
```

---

## 📊 Timeline Summary

```
Week 1-1.5    Phase 1: Foundation & Parsing
              - Grammar + Tokenizer + AST nodes + Parser
              - 80+ tokenization tests, 100+ parser tests

Week 2-2.5    Phase 2: Code Generation & Runtime
              - CodeGen + Expression Evaluator + All 40+ directives
              - 200+ runtime tests

Week 3-3.5    Phase 3: Engine Integration & Features
              - EdenEngine class + Caching + Loader
              - Test functions + Block inheritance + Namespaced imports
              - Type hints + Safe mode
              - 300+ integration tests

Week 4-4.5    Phase 4: Optimization & Polish
              - Performance optimization + Error messages
              - Full documentation (30 pages)
              - Migration tool + 6 examples
              - Benchmark suite

Week 5        Phase 5: Testing & Deployment
              - 500+ comprehensive tests
              - Security audit
              - Integration checklist
              - Ready for production

TOTAL: 4-5 weeks of focused development
```

---

## 🎯 Success Criteria (Definition of Done)

### **Functional**
- ✅ All 40+ directives working identically to current Eden
- ✅ Compiles to bytecode (not interpreted)
- ✅ Renders in < 10ms for typical templates
- ✅ Must-have features (tests, inheritance, namespaces, types, safe mode) all working
- ✅ Line-preserving error reporting with context

### **Quality**
- ✅ 500+ tests, > 95% coverage
- ✅ Zero performance regressions
- ✅ Security audit passed
- ✅ All edge cases handled gracefully

### **Documentation**
- ✅ 30+ pages of docs
- ✅ 6+ working examples
- ✅ Migration guide for Jinja2 users
- ✅ API reference complete

### **Integration**
- ✅ Can be used alongside current Eden
- ✅ Optional to enable (not breaking change)
- ✅ Easy migration path from old system

---

## 🔄 Development Workflow

### **Repository Structure (Outside eden/)**
```
c:\ideas\eden\eden_engine/
├── .git                    (separate git repo optional)
├── .gitignore
├── README.md             (quick start)
├── pyproject.toml        (dependencies)
├── pytest.ini
├── setup.py
├── IMPLEMENTATION_LOG.md (progress tracker - UPDATED DAILY)
└── [all source dirs above]
```

### **Daily Standup Template**
```
DATE: 2026-03-XX

COMPLETED TODAY:
- [ ] [Milestone] - Description

IN PROGRESS:
- [ ] [Milestone] - Expected completion

BLOCKERS:
- None / [Issue description]

TEST STATUS:
- 150 / 500 tests passing
- Line coverage: 45%
- Performance: On track
```

### **Code Organization Principles**
- ✅ Each module has single responsibility
- ✅ No circular imports
- ✅ Extensive docstrings (Google style)
- ✅ Type hints on all public APIs
- ✅ Custom exceptions for clear error handling
- ✅ Tests colocated with implementation (neighboring test_*.py files)

---

## 🚀 Quick Start for Dev Work

### **Phase 1 Focus (Week 1)**
```
1. Create eden_engine/ directory structure
2. Define Lark grammar in grammar/eden_directives.lark
3. Implement EdenLexer with Lark
4. Write 50+ grammar tests
5. Define all AST node classes
6. Write 100+ parser tests

DAILY COMMIT: "Day 1: Lark grammar + lexer foundation"
```

### **Phase 2 Focus (Week 2)**
```
1. Implement CodeGenerator for AST → Python
2. Implement ExpressionEvaluator with simpleeval
3. Implement RenderContext for scoping
4. Implement all 40+ directive handlers
5. Wire everything together in EdenEngine stub

DAILY COMMIT: "Day 1: CodeGen + Expression evaluator"
```

### **Phase 3 Focus (Week 3)**
```
1. Complete EdenEngine class
2. Implement Cache + Loader
3. Add test functions (@is defined, etc)
4. Add block inheritance (@extends, @block)
5. Add namespaced imports (@import as)
6. Add type validation
7. Add safe mode

DAILY COMMIT: "Day 1: EdenEngine + caching"
```

### **Phase 4 Focus (Week 4)**
```
1. Performance profiling + optimization
2. Write all documentation
3. Create examples
4. Build migration tool
5. Error message polish

DAILY COMMIT: "Day 1: Docs + examples"
```

### **Phase 5 Focus (Week 5)**
```
1. Write comprehensive test suite (500+ tests)
2. Run security audit
3. Performance regression testing
4. Integration testing with Eden
5. Final checklist before production

DAILY COMMIT: "Day 1: Comprehensive test suite"
```

---

## 📝 Notes & Considerations

### **Design Decisions**
1. **Why Lark?** — PEG parser generators eliminate manual tokenizer bugs; grammar is self-documenting
2. **Why CodeGen to Python?** — Compiled bytecode is 10-100x faster than tree-walking interpretation
3. **Why separate from eden/?** — Allows testing + iteration without breaking main package
4. **Why not use existing Jinja2 engine?** — Too much cruft for our brace syntax; cleaner to build custom
5. **Why safe mode now?** — Security-conscious design from day 1; easier than retrofitting

### **Known Challenges**
1. **Whitespace handling** — Must preserve HTML formatting; tricky with brace blocks
2. **Circular template imports** — @import A imports B imports A → infinite loop
3. **IDE Integration** — Type hints help, but no real-time validation in editors (yet)
4. **Async templates** — If components call async functions, entire render becomes async
5. **Error messages** — Balancing helpful vs noisy; test thoroughly

### **Testing Strategy**
- **Unit tests first** (lexer/parser/codegen) → catch bugs early
- **Integration tests second** (full template scenarios)
- **Performance tests third** (regression detection)
- **Security tests last** (critical path, non-negotiable)

### **Deployment Strategy**
- Build as standalone package (`eden-templating-engine`)
- Can be used without full Eden framework
- Eventually merge as core module in Eden 2.0
- Maintain backward compatibility layer for old Jinja2 approach (if desired)

---

## ✅ Checklist Before Starting Code

- ✅ Review this plan with team
- ✅ Set up eden_engine/ directory
- ✅ Create git repo (or branch strategy)
- ✅ Install dependencies: lark, simpleeval, markupsafe
- ✅ Set up pytest + CI/CD
- ✅ Create IMPLEMENTATION_LOG.md
- ✅ Schedule weekly syncs to review progress
- ✅ Define code review process

---

**This is your roadmap. Ready to start Phase 1?**
