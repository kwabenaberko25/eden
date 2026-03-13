# Eden Templating Engine - Syntax Standardization

> Critical decision before Phase 1: Establish ONE consistent syntax style for all directives

---

## 🚨 The Problem

**Current inconsistencies in examples:**

```html
<!-- Mix 1: Some with parens, some without -->
@block head { ... }            ← No parentheses
@if (user is defined) { ... }  ← With parentheses
@yield "page_title" { ... }    ← Space-separated, no parens

<!-- Mix 2: Inconsistent argument style -->
@component(card.product, {})   ← Using parentheses
@slot content { ... }           ← No parentheses
@for (item in items) { ... }   ← With parentheses
```

**This breaks the parser design** — the Lark grammar needs ONE mode of operation, not multiple.

---

## 🎯 Three Viable Standard Options

### **Option A: Parentheses for ALL Arguments** (Most Explicit)

Structure: `@directive(arg1, arg2, ...) { body }`

**Pros:**
- ✅ Maximally explicit and predictable
- ✅ Familiar to JavaScript/Python developers
- ✅ Parser is simpler (everything in parens)
- ✅ Scales well to complex arguments
- ✅ IDE/syntax highlighting easier

**Cons:**
- ❌ More verbose for simple cases
- ❌ Looks heavier than needed

**Full Examples:**

```html
<!-- Control Flow -->
@if (user is defined) {
    <p>Hello</p>
}

@unless (user.banned) {
    <content />
}

@for (item in items) {
    <div>{{ item.name }}</div>
}

@switch (status) {
    @case ("pending") { ... }
    @case ("shipped") { ... }
}

<!-- Components & Inheritance -->
@component("card", { title: "Test" }) {
    @slot("content") {
        <p>Default</p>
    }
}

@extends("layouts/base") {
    @block("content") {
        <h1>Page</h1>
    }
    @block("footer") {
        <footer>© 2025</footer>
    }
}

@yield("page_title", "Default Title")

@block("header") {
    <header>...</header>
}

<!-- Data & Forms -->
@let("color", "#2563EB")

@csrf()

@checked(user.newsletter)

@if (loop.first) {
    <span>First</span>
}

<!-- Routing -->
@url("products.show", { id: product.id })

@active_link("admin.*", "active-page")

<!-- Assets -->
@css("/assets/app.css")
@js("/assets/app.js")
@vite()

<!-- Messages -->
@error("email")
@messages()
```

---

### **Option B: No Parentheses, Space-Separated** (Most Natural)

Structure: `@directive arg1 arg2 ... { body }`

**Inspired by:** Ruby, Vue, Blade

**Pros:**
- ✅ Cleanest, most readable for simple cases
- ✅ Feels modern and lightweight
- ✅ Great for single arguments
- ✅ Less "bracket fatigue"

**Cons:**
- ❌ Parser is more complex (variable-length args)
- ❌ Harder to distinguish where args end
- ❌ Ambiguous with complex expressions
- ❌ IDE autocomplete harder

**Full Examples:**

```html
<!-- Control Flow -->
@if user is defined {
    <p>Hello</p>
}

@unless user.banned {
    <content />
}

@for item in items {
    <div>{{ item.name }}</div>
}

@switch status {
    @case "pending" { ... }
    @case "shipped" { ... }
}

<!-- Components & Inheritance -->
@component "card" { title: "Test" } {
    @slot "content" {
        <p>Default</p>
    }
}

@extends "layouts/base" {
    @block "content" {
        <h1>Page</h1>
    }
    @block "footer" {
        <footer>© 2025</footer>
    }
}

@yield "page_title" "Default Title"

@block "header" {
    <header>...</header>
}

<!-- Data & Forms -->
@let "color" "#2563EB"

@csrf

@checked user.newsletter

@if loop.first {
    <span>First</span>
}

<!-- Routing -->
@url "products.show" { id: product.id }

@active_link "admin.*" "active-page"

<!-- Assets -->
@css "/assets/app.css"
@js "/assets/app.js"
@vite

<!-- Messages -->
@error "email"
@messages
```

---

### **Option C: Smart Hybrid** (Best of Both)

**Rule:** 
- **Expressions/conditions:** Always in parentheses `(expr)`
- **Identifiers/simple args:** No parentheses, space-separated
- **Mixed:** Only use parens when needed

**Pros:**
- ✅ Clean syntax for common case (identifiers)
- ✅ Safe for complex expressions (parens)
- ✅ Familiar from conditional syntax
- ✅ Good readability/conciseness balance

**Cons:**
- ⚠️ Requires learning the rule
- ⚠️ Parser slightly complex (two modes)
- ⚠️ Can feel inconsistent at first

**Full Examples:**

```html
<!-- Expressions: Always parentheses -->
@if (user is defined) {
    <p>Hello</p>
}

@unless (user.banned) {
    <content />
}

@for (item in items) {
    <div>{{ item.name }}</div>
}

@switch (status) {
    @case ("pending") { ... }
    @case ("shipped") { ... }
}

<!-- Identifiers/named args: No parentheses -->
@component card {
    @slot content {
        <p>Default</p>
    }
}

@component "card" title="Profile" {
    ...
}

@extends "layouts/base" {
    @block content {
        <h1>Page</h1>
    }
}

@yield "page_title" "Default Title"

@block header {
    <header>...</header>
}

@let color "#2563EB"

@csrf

@checked (user.newsletter)  ← Expression uses parens

@if (loop.first) {
    <span>First</span>
}

@url "products.show" id=product.id

@active_link "admin.*" class="active"

@css "/assets/app.css"
@js "/assets/app.js"

@error "email"
```

---

## 📊 Comparison Matrix

| Criterion | Option A (Parens) | Option B (Space) | Option C (Hybrid) |
|-----------|-------------------|------------------|-------------------|
| **Explicit** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Readable** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Consistent** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Parser Complexity** | ⭐⭐⭐⭐⭐ (Simple) | ⭐⭐ (Complex) | ⭐⭐⭐ (Medium) |
| **Familiar to Dev** | ⭐⭐⭐⭐⭐ (JS/Python) | ⭐⭐⭐⭐ (Ruby/Vue) | ⭐⭐⭐⭐⭐ (Mixed) |
| **Extensibility** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| **IDE Support** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |

---

## 🎨 Aesthetic Comparison

### **Simple If Statement**

```html
<!-- Option A -->
@if (user is defined) {
    Hello
}
/* 3 lines, 30 chars of syntax */

<!-- Option B -->
@if user is defined {
    Hello
}
/* 3 lines, 20 chars of syntax */

<!-- Option C (same as B here) -->
@if (user is defined) {
    Hello
}
/* Hybrid uses parens for expressions */
```

### **Component with Multiple Args**

```html
<!-- Option A -->
@component("card", { title: "My Card", shadow: "lg" }) {
    Content here
}

<!-- Option B -->
@component "card" title="My Card" shadow="lg" {
    Content here
}

<!-- Option C -->
@component "card" title="My Card" shadow="lg" {
    Content here
}
```

### **Complex Expression**

```html
<!-- Option A -->
@if ((user.age > 18) && (user.is_verified is true)) {
    Access granted
}

<!-- Option B -->
@if user.age > 18 && user.is_verified is true {
    Access granted
}
/* Ambiguous: where do args end? */

<!-- Option C -->
@if ((user.age > 18) && (user.is_verified is true)) {
    Access granted
}
/* Clear: parens signal complex expression */
```

---

## ✅ My Recommendation: **Option C (Hybrid)**

### Why?

1. **Developer Experience** — Expressions in parens are familiar from all langs
2. **Readability** — Identifiers don't need parens, keeps it light
3. **Flexibility** — Scales from simple to complex
4. **Parser-Friendly** — Clear signal: `( )` means expression, space means identifier
5. **Future-Proof** — Easy to extend with new directives
6. **Aligns with Eden** — Modern yet predictable

### The Rule (Simple)

| Pattern | Example | Notes |
|---------|---------|-------|
| **Expressions** | `@if (expr)` | Use parens for boolean logic |
| **Identifiers** | `@block header` | No parens for names/IDs |
| **Strings** | `@extends "layout"` | Quoted as-is |
| **Key-value** | `title="Test"` | Standard HTML attr syntax |
| **Complex args** | `@component card {data}` | Object notation stays readable |

---

## 🔄 Impact on Implementation

### **Lark Grammar Changes**

**Option A (Parentheses):**
```
directive_stmt: "@" IDENTIFIER "(" args? ")" block
args: expr ("," expr)*
```
✅ Simple grammar, one rule

**Option B (Space-separated):**
```
directive_stmt: "@" IDENTIFIER args? block
args: (STRING | IDENTIFIER | expr)+
```
⚠️ Complex: ambiguous where args end

**Option C (Hybrid):**
```
directive_stmt: "@" IDENTIFIER 
                 ( "(" expr ")" | (STRING | IDENTIFIER)+ )? 
                 block
```
✅ Medium complexity, clear rules

---

## 🎬 Before Phase 1 Begins

**Action Items:**

1. ✅ **Choose syntax option** (A, B, or C)
2. ✅ **Document the rule** (one clear sentence)
3. ✅ **Update all examples** to use chosen syntax
4. ✅ **Finalize Lark grammar** based on choice
5. ✅ **Brief dev team** on syntax

---

## Proposed Standard (Option C - Hybrid)

### **Final Rule**

> **Expressions go in parentheses `(...)`. Identifiers and strings are space-separated. Arguments use natural syntax (key="value" or object notation).**

### **Examples with This Standard**

```html
<!-- ✅ GOOD: Consistent Hybrid -->

<!-- Expressions in parens -->
@if (user is defined) { }
@for (item in items) { }
@unless (user.banned) { }
@switch (status) { }

<!-- Identifiers/strings without parens -->
@block header { }
@extends "layouts/base"
@component "card"
@slot "content"

<!-- Arguments are natural -->
@component "card" title="Profile" shadow="lg" { }
@let color "#2563EB"
@yield "page_title" "Default"
@url "products.show" id=product.id

<!-- Complex expressions still use parens -->
@if ((user.age > 18) && (user.is_verified)) { }

<!-- ❌ WRONG: Mixing -->
@if user is defined { }        ← Expression without parens
@component(card)               ← Identifier in parens
@block(header)                 ← Identifier in parens
```

---

## 📝 Updated Example (Option C Applied)

```html
<!-- layouts/app.html using consistent syntax -->
@extends "layouts/base"

@block head {
    <title>@yield "page_title" "My Store"</title>
}

@block content {
    @if (user is defined) {
        <nav>
            <span>{{ user.name | truncate(20) }}</span>
            
            @if (user.is_admin) {
                <a href="@url('admin.dashboard')">Admin</a>
            }
        </nav>
    }
    
    @for (product in products) {
        @component "card" 
            title=product.name 
            featured=(loop.index1 == 1) 
        {
            @slot "content" {
                <button>Add to Cart</button>
            }
        }
        
        @if (loop.even) {
            <hr>
        }
    }
}
```

---

## 🎯 Next Steps

**Which option do you prefer?**

- **A (Parentheses)** — Most explicit, parser simplest
- **B (Space)** — Most natural, parser harder
- **C (Hybrid)** — Best balance, clear rules

Once chosen, I'll:
1. Rewrite all examples in the chosen syntax
2. Update the implementation plan with final grammar
3. Create a syntax reference guide for developers
4. Ready to begin Phase 1 with consistent design

**Let me know your call.** This decision cascades into the entire engine architecture.
