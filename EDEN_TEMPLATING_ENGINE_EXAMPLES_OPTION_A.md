# Eden Templating Engine - Complete Examples (Option A - Consistent)

> All directives follow one pattern: `@directive(args) { body }`

---

## Example 1: Base Layout

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    
    @block("head") {
        <title>@yield("page_title", "My Store")</title>
    }
    
    @css("/assets/tailwind.css")
    @css("/assets/app.css")
</head>
<body>
    @if (user is defined) {
        <nav>
            <span>{{ user.name }}</span>
            @auth() {
                <a href="@url('auth.logout')">Logout</a>
            }
            @guest() {
                <a href="@url('auth.login')">Login</a>
            }
        </nav>
    }
    
    @block("content") { }
    
    @block("footer") {
        <footer>&copy; 2025</footer>
    }
    
    @js("/assets/app.js")
    @vite()
</body>
</html>
```

---

## Example 2: Product Listing (Full Page)

```html
@extends("layouts/app.html")

@import("components/cards.html", {"as": "card"})
@import("includes/filters.html", {"as": "filters"})

@block("head") {
    <title>Products</title>
    @super()
}

@block("content") {
    <div class="container">
        <h1>Products</h1>
        
        <!-- Sidebar with filters -->
        <aside>
            @component(filters.category_filter, {
                "categories": categories,
                "selected": current_category
            }) { }
        </aside>
        
        <!-- Product Grid -->
        <main>
            @if (products is empty) {
                <p>No products found</p>
            } @else {
                <div class="grid">
                    @for (product in products) {
                        @component(card.product_card, {
                            "product": product,
                            "featured": (loop.index1 == 1)
                        }) {
                            @slot("price") {
                                ${{ product.price }}
                            }
                            
                            @slot("actions") {
                                @if (product.in_stock is true) {
                                    <button class="btn-primary">
                                        Add to Cart
                                    </button>
                                } @else {
                                    <button disabled>Out of Stock</button>
                                }
                            }
                        }
                        
                        @if (loop.even) {
                            <hr>
                        }
                    }
                </div>
            }
            
            <!-- Pagination -->
            <div class="pagination">
                @for (page in pagination.pages) {
                    @if ((page == pagination.current)) {
                        <span class="active">{{ page }}</span>
                    } @else {
                        <a href="@url('products.index', {'page': page})">
                            {{ page }}
                        </a>
                    }
                }
            </div>
        </main>
    </div>
}
```

---

## Example 3: Reusable Component

```html
<!-- components/product_card.html -->
@component("product_card", {"product": null, "featured": false}) {
    {{ product.name | truncate(40) }}
    
    @if (featured is true) {
        <span class="featured-badge">Featured</span>
    }
    
    <div class="price">
        @slot("price") {
            ${{ product.price }}
        }
    </div>
    
    <div class="rating">
        @if (product.rating is defined) {
            ⭐ {{ product.rating }}/5
        } @else {
            <p>No ratings</p>
        }
    </div>
    
    <div class="actions">
        @slot("actions") {
            <button>Add to Cart</button>
        }
    </div>
}
```

---

## Example 4: Form With Validation

```html
<form method="POST" action="@url('users.store')">
    @csrf()
    
    <div class="form-group">
        <label>Email</label>
        <input 
            type="email" 
            name="email"
            value="@old('email', '')"
        >
        @error("email") {
            <span class="error">{{ messages.email }}</span>
        }
    </div>
    
    <div class="form-group">
        <label>
            <input type="checkbox" name="newsletter" @checked(user.newsletter) { checked }>
            Subscribe to newsletter
        </label>
    </div>
    
    <div class="form-group">
        <label>Country</label>
        <select name="country_id">
            @for (country in countries) {
                <option 
                    value="{{ country.id }}"
                    @selected((country.id == user.country_id)) { selected }
                >
                    {{ country.name }}
                </option>
            }
        </select>
    </div>
    
    <button type="submit">Save</button>
</form>
```

---

## Example 5: Admin Dashboard

```html
@extends("layouts/admin.html")

@block("content") {
    @unless (user.is_admin is true) {
        <div class="error">Access Denied</div>
    } @else {
        <!-- Stats Cards -->
        <div class="stats">
            @for (stat in stats) {
                <div class="stat-card">
                    <h3>{{ stat.label }}</h3>
                    <div class="value">{{ stat.value | number_format }}</div>
                    @if (stat.trend is divisible_by(10)) {
                        <span class="trend">{{ stat.trend }}%</span>
                    }
                </div>
            }
        </div>
        
        <!-- Orders Table -->
        <table>
            <thead>
                <tr>
                    <th>Order</th>
                    <th>Customer</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
                @for (order in orders) {
                    <tr>
                        <td>#{{ order.id }}</td>
                        <td>{{ order.customer.name }}</td>
                        <td>
                            @switch (order.status) {
                                @case ("pending") {
                                    <span class="badge-warning">Pending</span>
                                }
                                @case ("completed") {
                                    <span class="badge-success">Completed</span>
                                }
                                @default {
                                    <span>{{ order.status }}</span>
                                }
                            }
                        </td>
                    </tr>
                } @empty {
                    <tr><td colspan="3">No orders</td></tr>
                }
            </tbody>
        </table>
    }
}
```

---

## Example 6: Nested Components With Slots

```html
@component("card", {"title": "User Profile", "shadow": "lg"}) {
    @slot("header") {
        <img src="{{ user.avatar }}" alt="Avatar">
    }
    
    @slot("body") {
        <h2>{{ user.name }}</h2>
        <p>{{ user.email }}</p>
        
        @if (user.bio is defined) {
            <p>{{ user.bio | truncate(100) }}</p>
        }
    }
    
    @slot("footer") {
        <button class="btn-primary">Edit</button>
        <button class="btn-danger">Delete</button>
    }
}
```

---

## Example 7: Type-Safe Context

```html
<!-- Python Context -->
@let("context_schema_user", "UserSchema")
@let("context_schema_posts", "PostSchema[]")

<!-- Template Uses TypedDict -->
@if (user is defined) {
    <!-- IDE knows user.name is str, user.age is int -->
    <h1>{{ user.name }}</h1>
    <p>Age: {{ user.age }}</p>
    
    <!-- IDE warns if access non-existent field -->
    <!-- {{ user.unknown_field }} - ERROR: field not in schema -->
}

@for (post in posts) {
    <!-- IDE knows post has: id, title, content, created_at -->
    <article>
        <h2>{{ post.title }}</h2>
        <time>{{ post.created_at | date('Y-m-d') }}</time>
    </article>
}
```

---

## Example 8: Safe Mode (User-Generated Content)

```html
<!-- Newsletter template (user-generated) -->
<!-- STRICT MODE: Only safe directives allowed -->

<div class="newsletter">
    <h1>{{ title | uppercase }}</h1>
    
    <!-- @if allowed -->
    @if (show_content) {
        <p>{{ description | truncate(200) }}</p>
    }
    
    <!-- @for allowed -->
    @for (item in items) {
        @component("newsletter_item", {"item": item}) { }
    }
    
    <!-- FORBIDDEN in safe mode: -->
    <!-- @let x = value — no variable assignment -->
    <!-- {{ user.method() }} — no method calls -->
    <!-- @import ... — no imports -->
</div>
```

---

## Example 9: Complete Form Page

Form submission with validation, field rendering, and error messages:

```html
<!-- Extends admin base layout -->
@extends("layouts/admin.html")

<!-- Page title -->
@block("page_title") {
    Edit User Profile
}

<!-- Main content -->
@block("content") {
    <div class="container mx-auto py-8">
        <h1>Edit User Profile</h1>
        
        <!-- Display general form errors -->
        @if (messages.form_error) {
            <div class="alert alert-danger">
                {{ messages.form_error }}
            </div>
        }
        
        <!-- User form -->
        <form method="POST" action="@url('users.update', {'id': user.id})" class="form-card">
            @csrf()
            
            <!-- Name field -->
            <div class="form-group">
                <label for="name" class="form-label">Full Name</label>
                <input 
                    type="text" 
                    id="name"
                    name="name"
                    value="@old('name', user.name)"
                    class="form-control"
                    required
                >
                @error("name") {
                    <span class="error-message">{{ messages.name }}</span>
                }
            </div>
            
            <!-- Email field -->
            <div class="form-group">
                <label for="email" class="form-label">Email Address</label>
                <input 
                    type="email" 
                    id="email"
                    name="email" 
                    value="@old('email', user.email)"
                    class="form-control"
                    required
                >
                @error("email") {
                    <span class="error-message">{{ messages.email }}</span>
                }
            </div>
            
            <!-- Phone field (optional) -->
            <div class="form-group">
                <label for="phone" class="form-label">Phone (Optional)</label>
                <input 
                    type="tel" 
                    id="phone"
                    name="phone"
                    value="@old('phone', user.phone)"
                    class="form-control"
                    placeholder="+1 (555) 000-0000"
                >
                @error("phone") {
                    <span class="error-message">{{ messages.phone }}</span>
                }
            </div>
            
            <!-- Country select -->
            <div class="form-group">
                <label for="country" class="form-label">Country</label>
                <select name="country_id" id="country" class="form-control">
                    <option value="">-- Select Country --</option>
                    @for (country in countries) {
                        <option 
                            value="{{ country.id }}"
                            @selected((country.id == @old('country_id', user.country_id))) { selected }
                        >
                            {{ country.name }}
                        </option>
                    }
                </select>
                @error("country_id") {
                    <span class="error-message">{{ messages.country_id }}</span>
                }
            </div>
            
            <!-- Bio textarea -->
            <div class="form-group">
                <label for="bio" class="form-label">Bio</label>
                <textarea 
                    id="bio"
                    name="bio"
                    class="form-control"
                    rows="5"
                    placeholder="Tell us about yourself..."
                >@old('bio', user.bio)</textarea>
                @error("bio") {
                    <span class="error-message">{{ messages.bio }}</span>
                }
            </div>
            
            <!-- Newsletter checkbox -->
            <div class="form-group checkbox-group">
                <label>
                    <input 
                        type="checkbox" 
                        name="newsletter"
                        value="yes"
                        @checked(@old('newsletter', user.newsletter)) { checked }
                    >
                    <span>Subscribe to our newsletter</span>
                </label>
            </div>
            
            <!-- User role (radio buttons) -->
            <div class="form-group">
                <label class="form-label">User Role</label>
                <div class="radio-group">
                    <label>
                        <input 
                            type="radio" 
                            name="role"
                            value="admin"
                            @checked((@old('role', user.role) == 'admin')) { checked }
                        >
                        <span>Administrator</span>
                    </label>
                    <label>
                        <input 
                            type="radio" 
                            name="role"
                            value="editor"
                            @checked((@old('role', user.role) == 'editor')) { checked }
                        >
                        <span>Editor</span>
                    </label>
                    <label>
                        <input 
                            type="radio" 
                            name="role"
                            value="viewer"
                            @checked((@old('role', user.role) == 'viewer')) { checked }
                        >
                        <span>Viewer</span>
                    </label>
                </div>
                @error("role") {
                    <span class="error-message">{{ messages.role }}</span>
                }
            </div>
            
            <!-- Permissions (multiple checkboxes) -->
            @if (permissions count > 0) {
                <div class="form-group">
                    <label class="form-label">Permissions</label>
                    <div class="checkbox-group">
                        @for (permission in permissions) {
                            <label>
                                <input 
                                    type="checkbox" 
                                    name="permissions[]"
                                    value="{{ permission.id }}"
                                    @checked(user.permissions contains permission.id) { checked }
                                >
                                <span>{{ permission.name }}</span>
                            </label>
                        }
                    </div>
                </div>
            }
            
            <!-- Form actions -->
            <div class="form-actions">
                <button 
                    type="submit"
                    class="btn btn-primary"
                    @disabled(form.is_submitting) { disabled }
                >
                    @if (form.is_submitting) {
                        <span>Saving...</span>
                    } @else {
                        <span>Save Changes</span>
                    }
                </button>
                
                <a href="@url('users.show', {'id': user.id})" class="btn btn-secondary">
                    Cancel
                </a>
            </div>
        </form>
    </div>
}

<!-- Page-specific CSS -->
@block("styles") {
    <style>
        .form-card {
            background: white;
            border-radius: 8px;
            padding: 24px;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        .form-label {
            display: block;
            font-weight: 600;
            margin-bottom: 8px;
        }
        
        .error-message {
            display: block;
            color: #dc2626;
            font-size: 0.875rem;
            margin-top: 4px;
        }
        
        .form-actions {
            display: flex;
            gap: 12px;
            margin-top: 28px;
        }
    </style>
}
```

---

## Syntax Examples (Option A - All Consistent)


```html
<!-- Control Flow -->
@if (condition) { ... }
@unless (condition) { ... }
@for (item in items) { ... }
@switch (value) { @case ("x") { ... } }

<!-- Components & Slots -->
@component("name", {"prop": "value"}) { 
    @slot("name") { ... }
}

<!-- Inheritance -->
@extends("layout.html")
@block("name") { ... }
@yield("name", "default")
@super()
@include("partial.html")

<!-- Data -->
@let("var", "value")
@old("field", "default")
@json(data)

<!-- Forms -->
@csrf()
@checked(condition) { checked }
@selected(condition) { selected }
@error("field") { ... }

<!-- Routing -->
@url("route.name", {"id": 1})
@active_link("pattern", "class")

<!-- Auth -->
@auth() { ... }
@guest() { ... }

<!-- Assets -->
@css("/file.css")
@js("/file.js")
@vite()

<!-- Test Functions -->
@if (value is defined) { }
@if (list is empty) { }
@if (num is odd) { }
@if (num is divisible_by(5)) { }

<!-- Loop Helpers -->
loop.index       (0-based)
loop.index1      (1-based)
loop.first       (boolean)
loop.last        (boolean)
loop.even        (boolean)
loop.odd         (boolean)
loop.length      (count)
```

---

## ✅ Consistency Guarantee

**Every directive follows this pattern:**
```
@directive(argument1, argument2, ...) { body }
```

**No exceptions. No special cases. Crystal clear.**

---

## 🎯 Benefits of Consistency

1. **Easy to Learn** — One pattern to remember
2. **Easy to Teach** — Show one example, all directives follow it
3. **Easy for IDE** — Clear token boundaries
4. **Easy to Extend** — Add new directives without redesigning
5. **Enterprise-Grade** — Professional, predictable, maintainable

---

**Status: All examples updated to Option A (Parentheses Everywhere - Consistent)**
