# Data Layer: The Eden ORM 🗄️

Eden features a zero-config, async-first ORM built on **SQLAlchemy 2.0**. It combines the power of raw SQL with the elegance of a Django-inspired API.

## Core Concepts

The Eden ORM lives by three pillars:

1. **Async by Default**: Every database interaction is non-blocking.
2. **Type-Inferred**: Use Python's type system to define your schema.
3. **Batteries Included**: Relationships, transactions, and migrations work out of the box.

---

## Defining Models

Model properties like `is_in_stock` are automatically handled during serialization.

### The Zen of Fields: `f()`

The `f()` helper is more than just a `mapped_column` alias; it's a metadata engine that flows through your entire app.

```python
name: Mapped[str] = f(
    max_length=100, 
    index=True, 
    label="Product Name", 
    placeholder="Enter name..."
)
```
- **DB Layer**: Sets length, index, and nullability.
- **UI Layer**: Sets labels, placeholders, and widget types for auto-forms.
- **Validation**: Enforces `max_length` in derived schemas.

---

## Real-world Example: Dashboard Stats

The power of Eden's ORM is best seen when building complex interfaces.

```python
from eden.db import Sum, Count, Q
from datetime import datetime, timedelta

async def get_sales_dashboard():
    month_ago = datetime.now() - timedelta(days=30)
    
    # Complex query with aggregates returning a typed dictionary
    stats = await Order.filter(
        Q(created_at__gte=month_ago) & ~Q(status="cancelled")
    ).aggregate(
        revenue=Sum("total_price"),
        order_count=Count("id"),
        avg_value=Sum("total_price") / Count("id")
    )
    
    # Returns: {'revenue': 12500.50, 'order_count': 42, 'avg_value': 297.63}
    return stats
```

---

## Unified Schema Integration

Eden bridges the gap between your **Validation Layer** (Schemas/Forms) and your **Data Layer** (Models).

You can bridge your **SQLAlchemy Models** and **Pydantic Schemas** with zero boilerplate.

```python
# 1. Export as Dictionary (with relationship control)
data = product.to_dict(include=["name", "category"], exclude=["internal_notes"])

# 2. Generate an Interactive Pydantic Schema
# This inherits all labels/validators from the f() fields
PublicProduct = Product.to_schema(exclude=["stock_threshold"])

# 3. Create model instance from validated Input (Pydantic/Form)
new_product = await Product.create_from(validated_data)
```

---

## Deep Dives

To continue learning about the Data Layer, explore these specialized guides:

- **[Querying & Lookups](orm-querying.md)**: Master the Django-style filter syntax and complex `Q` objects.
- **[Relationship Patterns](orm-relationships.md)**: Handling One-to-Many, Many-to-Many, and fixing N+1 problems.
- **[Transactions & Atomicity](orm-transactions.md)**: Using `@atomic` and manual session management.
- **[Migrations](orm-migrations.md)**: How to evolve your database schema with CLI tools.

---

**Next Steps**: [Authentication & Security](auth.md)
