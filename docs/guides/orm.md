# Data Layer: The Eden ORM 🗄️

Eden features a zero-config, async-first ORM built on **SQLAlchemy 2.0**. It combines the power of raw SQL with the elegance of a Django-inspired API.

## Core Concepts

The Eden ORM lives by three pillars:

1. **Async by Default**: Every database interaction is non-blocking.
2. **Type-Inferred**: Use Python's type system to define your schema.
3. **Batteries Included**: Relationships, transactions, and migrations work out of the box.

---

## Defining Models

Models are Python classes that inherit from `Model`. They use the `f()` helper for a "Zen" definition experience with automatic type inference.

```python
from eden import Model, f, Mapped

class Product(Model):
    __tablename__ = "products"
    
    name: Mapped[str] = f(max_length=100, index=True)
    description: Mapped[str] = f(nullable=True)
    price: Mapped[float] = f(default=0.0)
    stock: Mapped[int] = f(default=0)
    
    @property
    def is_in_stock(self) -> bool:
        return self.stock > 0
```

---

## Real-world Example: Dashboard Stats

The power of Eden's ORM is best seen when building complex interfaces.

```python
from eden.db import Sum, Count, Q
from datetime import datetime, timedelta

async def get_sales_dashboard():
    # 1. Define time window
    month_ago = datetime.now() - timedelta(days=30)
    
    # 2. Complex query with aggregates
    stats = await Order.filter(
        Q(created_at__gte=month_ago) & ~Q(status="cancelled")
    ).aggregate(
        revenue=Sum("total_price"),
        order_count=Count("id"),
        avg_value=Sum("total_price") / Count("id")
    )
    
    return stats
```

---

## Unified Schema Integration

Eden bridges the gap between your **Validation Layer** (Schemas/Forms) and your **Data Layer** (Models).

### Smart Conversion

You can easily convert models to Pydantic schemas or HTMX forms.

```python
# Generate a schema on the fly
PublicProduct = Product.to_schema(exclude=["stock_threshold"])

# Create model from validated input
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
