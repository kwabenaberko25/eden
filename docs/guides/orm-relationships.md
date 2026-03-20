# 🔗 Relationship Patterns

**Eden simplifies complex database associations with high-level abstractions that handle foreign keys, back-references, and eager loading automatically.**

---

## 🧠 Conceptual Overview

Relationships in Eden are first-class citizens. By combining SQLAlchemy's powerful mapping engine with Eden's **Automatic Join Inference**, you can query across tables as if they were a single unified object.

### Common Relationship Archetypes

```mermaid
graph LR
    subgraph "One-to-One"
        User --- Profile
    end
    
    subgraph "One-to-Many"
        Brand --- Product1
        Brand --- Product2
    end
    
    subgraph "Many-to-Many"
        Student1 --- ClassA
        Student2 --- ClassA
        Student1 --- ClassB
    end
```

---

## 🏗️ Core Relationship Helpers

Eden provides high-level helpers that simplify the standard SQLAlchemy boilerplate.

### Reference vs. Relationship: What's the difference?

While they look similar, they have two distinct responsibilities:

1.  **`Reference` (The One-Liner)**: This is the "heavy lifter." It **creates the Database Column** (the Foreign Key) and the ORM link in one go. Use this on the side that "belongs to" the other (e.g., `Teacher` belongs to `User`).
2.  **`Relationship` (The Navigator)**: This does **not** create any database columns. it simply tells Eden how to navigate to the other model. Use this on the side that doesn't have the ID.

| Helper | Action | Where to use? |
| :--- | :--- | :--- |
| **`Reference`** | **Creates FK Column** + ORM Link | The "Child" side (has the ID). |
| **`Relationship`**| Just Navigates | The "Parent" side (no ID). |

---

## 🏗️ Core Relationship Types

### 1. One-to-Many (1:N)
The most common pattern. A single parent has many children (e.g., a Company has many Employees).

```python
from typing import List
from eden.db import Model, f, Mapped, relationship

class Company(Model):
    name: Mapped[str] = f()
    # One Company -> Many Employees
    employees: Mapped[List["Employee"]] = relationship(back_populates="company")

class Employee(Model):
    name: Mapped[str] = f()
    # 🌟 The Eden Way: Reference() handles the company_id for you!
    company: Mapped["Company"] = Reference(back_populates="employees")
```

### 2. One-to-One (1:1)
Required when one record is strictly linked to exactly one other record (e.g., a `User` and their `Teacher` profile).

```python
class User(Model):
    name: Mapped[str] = f()
    # Relationship points back; uselist=False makes it 1:1
    teacher: Mapped["Teacher"] = relationship("Teacher", back_populates="user", uselist=False)

class Teacher(Model):
    staff_id: Mapped[str] = f(unique=True)
    # Reference creates the user_id column + link
    user: Mapped["User"] = Reference(back_populates="teacher")
```

### 3. Many-to-Many (N:M)
Requires an intermediate **Association Table**. Eden manages this link transparently.

```python
from sqlalchemy import Table, Column, Integer, ForeignKey

# The bridge table
user_groups = Table(
    "user_groups",
    Model.metadata,
    Column("user_id", Integer, ForeignKey("users.id")),
    Column("group_id", Integer, ForeignKey("groups.id"))
)

class User(Model):
    name: Mapped[str] = f()
    groups: Mapped[List["Group"]] = relationship(
        secondary=user_groups, back_populates="users"
    )

class Group(Model):
    name: Mapped[str] = f()
    users: Mapped[List["User"]] = Relationship(
        secondary=user_groups, back_populates="groups"
    )

---

## ⚙️ Key Configuration Attributes

Understanding these two attributes is critical for mastering Eden's data layer.

### 1. `back_populates` (The Sync Manager)
This links two relationships together so they stay in sync at runtime. Without it, assigning a `User` to a `Teacher` wouldn't instantly update the `User.teacher` attribute in memory.

*   **Rule**: Must be on **both** sides.
*   **Target**: Must point to the attribute name on the *other* model.

### 2. `uselist` (The List Control)
Decides if an attribute returns a single object or a collection.

*   **`uselist=True` (Default)**: Returns a `list`. Used for 1:N and N:M.
*   **`uselist=False`**: Returns a **single object**. Used for 1:1.

---
```

---

## 🚀 Advanced Querying: Automatic Join Inference

Eden's `QuerySet` can "see" through your relationships. You can filter by related model attributes using the `__` separator.

```python
# Find all employees working for 'Eden Corp'
# Eden automatically performs the INNER JOIN under the hood
staff = await Employee.filter(company__name="Eden Corp").all()

# Logic: Find posts written by users with a specific role
featured_posts = await Post.filter(author__role="editor").all()
```

---

## ⚡ Solving the N+1 Problem: Eager Loading

The **N+1 problem** occurs when you load a list of items and then trigger a separate database query for *each* related object. In an async environment, this is catastrophic for performance.

### Loading Strategies

| Strategy | SQLAlchemy Method | Description |
| :--- | :--- | :--- |
| **`selectinload`** | `selectinload()` | **Default**. Emits a second bulk query using `IN (...)`. Fast and safe for collections. |
| **`joinedload`** | `joinedload()` | Uses a `LEFT OUTER JOIN` in the same query. Best for 1:1 or 1:N with few results. |
| **`subqueryload`** | `subqueryload()` | Emits a subquery to fetch children. Used for complex legacy schemas. |

### Using `.prefetch()`
Eden's `.prefetch()` helper uses `selectinload` by default.

```python
# Query 1: Fetch 100 posts
# Query 2: Fetch all authors for those 100 posts in ONE query
posts = await Post.query().prefetch("author", "comments").all()

for post in posts:
    # This access is now instantaneous (already loaded in memory)
    print(f"{post.title} by {post.author.name}")
```

### Deep Prefetching
Use dot notation to pre-load nested relationships (e.g., `Post` -> `Author` -> `Brand`).
```python
results = await Post.query().prefetch("author.brand").all()
```

---

## 💡 Best Practices

1.  **Explicit `back_populates`**: Always define `back_populates` on both sides of a relationship to ensure SQLAlchemy's identity map remains consistent.
2.  **Default to `selectinload`**: For async applications, `selectinload` is almost always the most efficient choice as it avoids the massive result-set multiplication of `joinedload`.
3.  **Unique Constraints for 1:1**: On a One-to-One relationship, always ensure the foreign key column is marked as `unique=True` in the child model.

---

**Next Steps**: [Transactions & Atomicity](orm-transactions.md)
