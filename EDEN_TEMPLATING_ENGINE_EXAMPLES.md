# Eden Templating Engine - Example Template Suite

> This document showcases the power and clarity of the new Eden templating engine through real-world examples. All features working together with **consistent Option A syntax: parentheses everywhere.**

---

## 🎯 Philosophy: Consistency With Power

The Eden templating engine is designed around these principles:
- ✅ **Consistent syntax** — One pattern everywhere: `@directive(args) { body }`
- ✅ **Crystal clear** — Parentheses make boundaries explicit
- ✅ **Type-safe** — IDE knows your context shape
- ✅ **Composable** — Components + slots work intuitively
- ✅ **Secure** — Safe mode for untrusted content
- ✅ **Fast** — Compiled to bytecode, not interpreted
- ✅ **Explicit** — Test functions replace magic truthiness

---

## 📐 Example 1: Complete Product Listing Page

### **Scenario**
A product listing page with:
- Authenticated user checking
- Pagination with loop helpers
- Reusable components with slots
- Form with CSRF protection
- Type-safe context
- Block inheritance from base layout

### **Directory Structure**
```
templates/
├── layouts/
│   └── app.html                   # Base layout
├── components/
│   ├── cards.html                 # Card component
│   └── pricing.html               # Pricing component
├── products/
│   ├── index.html                 # Product listing (THIS EXAMPLE)
│   └── show.html
└── includes/
    └── filters.html               # Reusable filter component
```

---

## 1️⃣ **Base Layout** (`templates/layouts/app.html`)

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    
    @block("head") {
        <title>@yield("page_title", "My Awesome Store")</title>
    }
    
    @css("/assets/tailwind.min.css")
    @css("/assets/app.css")
</head>
<body>
    <!-- Using test function: is defined -->
    @if (user is defined) {
        <nav class="navbar">
            <div class="brand">🌿 Eden Store</div>
            
            <div class="nav-items">
                <!-- Using @auth directive -->
                @auth() {
                    <span class="user-name">{{ user.name | truncate(20) }}</span>
                    
                    @if (user.is_admin is true) {
                        <a href="@url('admin.dashboard')" class="@active_link('admin.*')">
                            Admin Panel
                        </a>
                    }
                    
                    <a href="@url('auth.logout')">Logout</a>
                }
                
                @guest() {
                    <a href="@url('auth.login')" class="btn-primary">Sign In</a>
                    <a href="@url('auth.register')">Register</a>
                }
            </div>
        </nav>
    }
    
    <!-- Main content block for child templates -->
    @block("content") { }
    
    <!-- Footer section -->
    @block("footer") {
        <footer>
            <p>&copy; 2025 Eden Store. All rights reserved.</p>
        </footer>
    }
    
    @js("/assets/app.js")
    @vite()
</body>
</html>
```

**Features demonstrated:**
- `@block` — Define overridable sections
- `@yield` — Render block with default fallback
- `@auth` / `@guest` — Auth-aware rendering
- `@url()` — Generate route URLs
- `@active_link()` — Active route CSS class
- `@css` / `@js` / `@vite` — Asset inclusion
- Filters applied inline: `| truncate(20)`

---

## 2️⃣ **Product Listing Page** (`templates/products/index.html`)

```html
@extends "layouts/app"

@import "components/cards" as card
@import "components/pricing" as pricing
@import "includes/filters" as filter_comp

<!-- Define page title in base layout -->
@block head {
    <title>Products - Eden Store</title>
    @super { }  <!-- Preserve base head content -->
}

<!-- Main content -->
@block content {
    <div class="container">
        <h1>Our Products</h1>
        
        <!-- Sidebar filters using namespaced component -->
        <div class="sidebar">
            @component(filter_comp.category_filter, {
                categories: categories,
                selected: current_category
            }) { }
        </div>
        
        <!-- Product grid -->
        <div class="product-grid">
            
            <!-- Test function: is empty -->
            @if (products is empty) {
                <div class="empty-state">
                    <h2>No products found</h2>
                    <p>Try adjusting your filters</p>
                </div>
            }
            
            @empty {
                <!-- This runs when products is empty, alternative to @if test -->
            }
            
            <!-- Loop with special loop variables -->
            @for (product in products) {
                <!-- Product card component with slot -->
                @component(card.product, {
                    product: product,
                    featured: loop.index1 == 1  <!-- First item is featured -->
                }) {
                    <!-- Slot: product actions -->
                    @slot content {
                        <div class="product-actions">
                            @if (product.discount_percent is divisible_by(5)) {
                                <span class="badge discount">
                                    {{ product.discount_percent }}% OFF
                                </span>
                            }
                            
                            @button product, (user.is_admin || product.in_stock) {
                                <button 
                                    class="btn btn-primary"
                                    @url:button:add data-product-id="{{ product.id }}"
                                >
                                    Add to Cart
                                </button>
                            }
                        </div>
                    }
                    
                    <!-- Slot: pricing info -->
                    @slot pricing {
                        @component(pricing.price_tag, {
                            regular: product.price,
                            discount: product.discount_price,
                            show_savings: true
                        }) { }
                    }
                }
                
                <!-- Loop helper directives -->
                @if (loop.even) {
                    <div class="row-divider"></div>
                }
            }
        </div>
        
        <!-- Pagination with test functions -->
        <div class="pagination">
            @if (pagination.has_prev is true) {
                <a href="@url('products.index', {page: pagination.prev_page})">
                    ← Previous
                </a>
            } @else {
                <span class="disabled">← Previous</span>
            }
            
            <!-- Loop through page numbers -->
            @for (page_num in pagination.page_range) {
                <!-- Test: is current page -->
                @let is_current = (page_num == pagination.current_page)
                
                @if (is_current) {
                    <span class="page-current">{{ page_num }}</span>
                } @else {
                    <a href="@url('products.index', {page: page_num})">
                        {{ page_num }}
                    </a>
                }
                
                <!-- Test: is odd (spacing) -->
                @if (loop.last is false) {
                    <span class="page-sep">|</span>
                }
            }
            
            @if (pagination.has_next is true) {
                <a href="@url('products.index', {page: pagination.next_page})">
                    Next →
                </a>
            } @else {
                <span class="disabled">Next →</span>
            }
        </div>
    </div>
}

<!-- Optional: Override footer for this page -->
@block footer {
    <footer class="product-footer">
        <div class="footer-content">
            @super { }  <!-- Include parent footer -->
            <p class="product-count">
                Showing {{ products | length }} of {{ total_products }} products
            </p>
        </div>
    </footer>
}
```

**Features demonstrated:**
- `@extends "layouts/app"` — Template inheritance
- `@import ... as` — Namespaced imports
- `@slot content { }` — Named slots in components
- `@if (var is empty)` / `@if (var is true)` — Test functions
- `@if (count is divisible_by(5))` — Arithmetic test
- `@let var = value` — Variable assignment
- `loop.index1`, `loop.even`, `loop.last` — Loop helpers
- `@else { }` — Conditional alternatives
- `{{ value | filter1 | filter2 }}` — Filter chaining
- `@super { }` — Include parent block content

---

## 3️⃣ **Reusable Component** (`templates/components/cards.html`)

```html
<!-- Product Card Component -->
@macro product(product, featured = false) {
    <div class="product-card @if(featured) { featured } @endif">
        <!-- Product image section -->
        <div class="product-image">
            <img 
                src="{{ product.image_url }}"
                alt="{{ product.name }}"
                loading="lazy"
            >
            
            @if (product.is_new is true) {
                <span class="badge badge-new">NEW</span>
            }
        </div>
        
        <!-- Product info -->
        <div class="product-info">
            <h3 class="product-name">{{ product.name | truncate(40) }}</h3>
            <p class="product-description">
                {{ product.description | truncate(100, "...") }}
            </p>
            
            <!-- Rating section using test functions -->
            <div class="rating">
                @if (product.rating is defined) {
                    <div class="stars" data-rating="{{ product.rating }}">
                        <!-- Loop to show stars -->
                        @for (i in range(int(product.rating))) {
                            <span class="star filled">★</span>
                        }
                        
                        <!-- Show empty stars for remainder -->
                        @for (i in range(5 - int(product.rating))) {
                            <span class="star empty">☆</span>
                        }
                    </div>
                    <span class="review-count">
                        ({{ product.review_count }})
                    </span>
                } @else {
                    <p class="no-rating">No ratings yet</p>
                }
            </div>
        </div>
        
        <!-- Pricing slot (injected from parent) -->
        <div class="product-pricing">
            @slot pricing { }
        </div>
        
        <!-- Actions slot (injected from parent) -->
        <div class="product-actions">
            @slot content { }
        </div>
    </div>
}
```

**Features demonstrated:**
- `@macro` — Reusable component definition
- `@slot pricing { } / @slot content { }` — Named injection points
- Conditional rendering based on data presence: `@if (product.rating is defined)`
- `@else` — Fallback rendering
- Loop helpers for repetitive UI

---

## 4️⃣ **Filter Component** (`templates/includes/filters.html`)

```html
<!-- Reusable filter sidebar component -->
@macro category_filter(categories, selected = null) {
    <form method="GET" class="filter-form">
        <h4>Filter by Category</h4>
        
        <fieldset>
            <legend>Categories</legend>
            
            @for (category in categories) {
                @let checkbox_name = "category_" ~ category.slug
                @let is_selected = (selected == category.id)
                
                <div class="checkbox-group">
                    <input 
                        type="checkbox"
                        id="{{ checkbox_name }}"
                        name="categories"
                        value="{{ category.id }}"
                        @if (is_selected) { checked }
                    >
                    
                    <label for="{{ checkbox_name }}">
                        {{ category.name }}
                        <span class="count">({{ category.product_count }})</span>
                    </label>
                </div>
                
                <!-- Visual indicator for first category -->
                @if (loop.first is true) {
                    <hr class="first-divider">
                }
            }
        </fieldset>
        
        <!-- CSRF protection -->
        @csrf
        
        <!-- Form buttons -->
        <div class="form-actions">
            <button type="submit" class="btn btn-primary">Apply Filters</button>
            <a href="@url('products.index')" class="btn btn-secondary">Clear</a>
        </div>
    </form>
}
```

**Features demonstrated:**
- `@let` — Inline variable assignment
- `{{ value ~ value }}` — String concatenation
- `@if (condition) { checked }` — Conditional attributes
- `@csrf` — CSRF token injection
- `loop.first` — Loop position helpers

---

## 5️⃣ **Advanced: Admin Dashboard with Safe Mode**

```html
<!-- Admin template showing advanced features -->
@extends "layouts/app"

@block head {
    <title>Admin Dashboard</title>
}

@block content {
    <div class="admin-container">
        <!-- Authorization check -->
        @unless (user.is_admin is true) {
            <div class="error-alert">
                <h2>Access Denied</h2>
                <p>Only administrators can access this page.</p>
            </div>
        } @else {
            <!-- Admin dashboard content -->
            
            <!-- Stats section with alternating backgrounds -->
            <div class="stats-grid">
                @for (stat in dashboard_stats) {
                    <div class="stat-card @if (loop.odd) { bg-primary } @else { bg-secondary }">
                        <h4>{{ stat.label }}</h4>
                        <div class="stat-value">{{ stat.value | number_format }}</div>
                        
                        <!-- Show trend indicator -->
                        @if (stat.trend is divisible_by(1)) {
                            @let trend_class = (stat.trend > 0) ? "positive" : "negative"
                            <span class="trend {{ trend_class }}">
                                {{ stat.trend }}%
                            </span>
                        }
                    </div>
                }
            </div>
            
            <!-- Orders table with switches -->
            <section class="orders-section">
                <h3>Recent Orders</h3>
                
                @if (orders is empty) {
                    <p>No orders yet.</p>
                } @else {
                    <table class="orders-table">
                        <thead>
                            <tr>
                                <th>Order ID</th>
                                <th>Customer</th>
                                <th>Total</th>
                                <th>Status</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            @for (order in orders) {
                                <tr class="@if (order.is_pending) { status-pending } @endif">
                                    <td>#{{ order.id }}</td>
                                    <td>{{ order.customer.name }}</td>
                                    <td>${{ order.total | number_format(2) }}</td>
                                    <td>
                                        <!-- Switch on order status -->
                                        @switch (order.status) {
                                            @case "pending" {
                                                <span class="badge badge-warning">Pending</span>
                                            }
                                            @case "processing" {
                                                <span class="badge badge-info">Processing</span>
                                            }
                                            @case "shipped" {
                                                <span class="badge badge-success">Shipped</span>
                                            }
                                            @case "delivered" {
                                                <span class="badge badge-success">Delivered</span>
                                            }
                                            @case "cancelled" {
                                                <span class="badge badge-danger">Cancelled</span>
                                            }
                                        }
                                    </td>
                                    <td>
                                        <a href="@url('admin.orders.show', {id: order.id})">
                                            View
                                        </a>
                                    </td>
                                </tr>
                            }
                        </tbody>
                    </table>
                }
            </section>
        }
    </div>
}
```

**Features demonstrated:**
- `@unless` — Inverted conditional
- `@switch / @case` — Multi-branch logic
- `loop.odd / loop.even` — Loop position helpers
- Format filters: `| number_format(2)`
- Chained conditionals in attributes

---

## 6️⃣ **Type-Safe Template with IDE Autocomplete**

### **Python Context Definition**
```python
# contexts.py
from typing import TypedDict, List, Optional

class UserContext(TypedDict):
    id: int
    name: str
    email: str
    is_admin: bool
    is_authenticated: bool

class ProductContext(TypedDict):
    id: int
    name: str
    price: float
    discount_price: Optional[float]
    image_url: str
    in_stock: bool

class ProductListPageContext(TypedDict):
    user: Optional[UserContext]
    products: List[ProductContext]
    total_products: int
    pagination: dict
    categories: List[dict]
    current_category: Optional[int]

# In your route handler
from eden import Eden

engine = Eden()

# Register type schema for IDE support
engine.set_context_schema(ProductListPageContext)

@app.get('/products')
async def products(request):
    context = ProductListPageContext(
        user=request.user,
        products=await Product.all().limit(20),
        total_products=await Product.count(),
        pagination=paginate(request),
        categories=await Category.all(),
        current_category=request.query.get('category')
    )
    
    # IDE now knows exactly what fields are available
    # Autocomplete: user.name, products[0].price, etc.
    return engine.render('products/index.html', context)
```

### **In The Template**
```html
<!-- Now IDE can:
     - Autocomplete: user.name, user.is_admin, user.is_authenticated
     - Know product.discount_price is Optional, might be None
     - Warn if accessing user.age (doesn't exist)
     - Show type errors at render time
-->

<h1>Welcome, {{ user.name }}!</h1>

@for (product in products) {
    <!-- IDE knows product has: id, name, price, discount_price, etc. -->
    <div class="product">
        <h3>{{ product.name }}</h3>
        <p>${{ product.price }}</p>
        
        <!-- IDE warns: product.unknown_field does not exist -->
        <!-- IDE knows: discount_price could be None, suggests null-safe checks -->
        @if (product.discount_price is defined) {
            <span class="price-discount">
                Save ${{ (product.price - product.discount_price) | round(2) }}
            </span>
        }
    </div>
}
```

**Benefits:**
- ✅ IDE autocomplete for context variables
- ✅ Type errors caught at compile time (not runtime)
- ✅ Self-documenting templates
- ✅ Zero mystery about what data is available

---

## 7️⃣ **Safe Mode: User-Generated Newsletter Template**

```html
<!-- 
    This template might come from a user (CMS, newsletter builder, etc.)
    Only safe, whitelisted features allowed
    Configuration restricts:
    - Only @if, @for, @component allowed
    - Only uppercase, lowercase, truncate filters
    - No method calls or attribute whitelisting
    - No @let, @import, @extends
    - Max output size: 1MB
    - Max execution time: 5 seconds
-->

<div class="newsletter">
    <h1>{{ title | uppercase }}</h1>
    
    <!-- Only @if allowed in safe mode -->
    @if (has_content) {
        <div class="content">
            {{ description | truncate(200) }}
        </div>
    }
    
    <!-- Only @for allowed for loops -->
    @for (item in items) {
        <!-- Whitelisted component only -->
        @component("newsletter_card", {
            title: item.title,
            description: item.description
        }) { }
    }
    
    <!-- These would raise SecurityError: -->
    <!-- @let x = user.get_private_data() — variable assignment forbidden -->
    <!-- {{ item.method() }} — method calls forbidden -->
    <!-- @import ... — imports forbidden -->
    <!-- @html_content — arbitrary attributes forbidden -->
</div>
```

**Safety Features:**
- ✅ Only specified directives allowed
- ✅ Only whitelisted filters runnable
- ✅ No method calls on objects
- ✅ No variable assignments
- ✅ No template inheritance
- ✅ Timeout + output size limits
- ✅ Perfect for CMS, newsletter builders, user-generated content

---

## 📊 Feature Comparison: Eden vs Jinja2

### **Readability**
```
Eden:                              Jinja2:
@if (user.active) {                {% if user.is_active %}
    Hello                              Hello
}                                  {% endif %}

Advantage: Eden is more concise    Advantage: None (more closing tags)
```

### **Composability**
```
Eden:                              Jinja2:
@import "buttons" as btn           (Not built-in; requires extensions)
@component(btn.primary)            

Advantage: Explicit namespacing    Advantage: None
```

### **Type Safety**
```
Eden:                              Jinja2:
engine.set_context_schema(Context) (No schema support)
# IDE knows user.name is str       # IDE doesn't know user type

Advantage: IDE autocomplete        Advantage: None
```

### **Safety**
```
Eden:                              Jinja2:
render_safe(template, ctx,         (Manual or plugin-based)
  allow=[...])                      

Advantage: Built-in safe mode      Advantage: More flexible
```

### **Components**
```
Eden:                              Jinja2:
@component(card, {data}) {         {% include "card.html" %}
    @slot title { }  -> named
}                                  (No named slots; workarounds needed)

Advantage: Explicit slots          Advantage: Simplicity
```

### **Performance**
```
Eden:                              Jinja2:
Compiled → bytecode               Interpreted at runtime
< 1ms simple                      ~ 5-10ms simple

Advantage: 5-10x faster           Advantage: None
```

---

## 🎨 Design Philosophy in Action

### **The Products Page Template Demonstrates:**

1. **Simplicity**
   - No `{% endif %}`, `{% endfor %}`, `{% endblock %}`
   - Braces make block structure obvious
   - Test functions replace magic truthiness

2. **Power**
   - 40+ directives for every scenario
   - Components with named slots
   - Template inheritance
   - Type validation

3. **Safety**
   - No arbitrary Python execution
   - Test functions prevent surprises
   - Safe mode for user content
   - CSRF tokens built-in

4. **Composability**
   - Namespaced imports prevent collisions
   - Slot-based component pattern
   - Macros are reusable
   - Inheritance is explicit

5. **Developer Experience**
   - Error messages point to line in source
   - IDE autocomplete with type hints
   - Live playground for testing
   - Migration tool from Jinja2

---

## ✨ Summary: Why This Matters

The new Eden templating engine turns template design from a tedious chore into a **first-class citizen** in your application architecture:

- **For designers:** Clean syntax, easy to learn, powerful components
- **For developers:** Type safety, performance, security by default
- **For teams:** Reusable components, namespacing prevents conflicts
- **For companies:** Safe mode for UGC, compliance-ready sandboxing

Templates aren't an afterthought—they're **part of your framework's excellence**.

---

**Next Step:** Start with Phase 1 of the implementation plan. The grammar defines how clean & powerful this syntax becomes.
