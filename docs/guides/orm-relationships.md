# Relationship Patterns 🔗

Eden handles complex database relationships with a mix of automatic inference and granular control.

## Overview

Relationships in Eden are defined using standard SQLAlchemy `Mapped` types and the `relationship()` function. Eden enhances this with **Automatic Join Inference** during filtering.

---

## One-to-Many / Many-to-One

This is the most common relationship. One "Parent" has many "Children".

```python
from typing import List
from eden.db import Model, f, Mapped, relationship

class Company(Model):
    __tablename__ = "companies"
    name: Mapped[str] = f()
    # One Company -> Many Employees
    employees: Mapped[List["Employee"]] = relationship(back_populates="company")

class Employee(Model):
    __tablename__ = "employees"
    name: Mapped[str] = f()
    company_id: Mapped[int] = f(foreign_key="companies.id")
    # Many Employees -> One Company
    company: Mapped["Company"] = relationship(back_populates="employees")
```

### Querying Across Relationships
Eden automatically joins tables when you use the `related__field` syntax.

```python
# Find employees working at 'Eden Corp'
# Eden infers the join from Employee to Company automatically
staff = await Employee.filter(company__name="Eden Corp")
```

---

## Many-to-Many (M2M)

Requires an association table. Eden allows you to manage these collections like standard Python lists.

```python
from sqlalchemy import Table, Column, Integer, ForeignKey

# Association Table
user_groups = Table(
    "user_groups",
    Model.metadata,
    Column("user_id", Integer, ForeignKey("users.id")),
    Column("group_id", Integer, ForeignKey("groups.id"))
)

class User(Model):
    __tablename__ = "users"
    name: Mapped[str] = f()
    groups: Mapped[List["Group"]] = relationship(
        secondary=user_groups, back_populates="users"
    )

class Group(Model):
    __tablename__ = "groups"
    name: Mapped[str] = f()
    users: Mapped[List["User"]] = relationship(
        secondary=user_groups, back_populates="groups"
    )
```

### Managing M2M Collections
```python
user = await User.get(1)
group = await Group.get(5)

# Add to relationship
await user.groups.append(group)

# Check membership
if group in await user.groups:
    print("User is in group")
```

---

## One-to-One

Useful for profiles or settings tables that extend a base model.

```python
class Profile(Model):
    __tablename__ = "profiles"
    bio: Mapped[str] = f()
    user_id: Mapped[int] = f(foreign_key="users.id", unique=True)
    
    # uselist=False makes it One-to-One
    user: Mapped["User"] = relationship(back_populates="profile", uselist=False)

class User(Model):
    __tablename__ = "users"
    profile: Mapped["Profile"] = relationship(back_populates="user", uselist=False)
```

---

## ⚡ Solving the N+1 Problem

The "N+1 Problem" occurs when you load a list of objects and then access a related object for each one, causing a separate database query for every row.

### The Problem (Slow)
```python
# Query 1: Fetch 100 employees
employees = await Employee.all()

for emp in employees:
    # Queries 2-101: Fetch company for each employee
    print(emp.company.name) 
```

### The Solution: `prefetch` (Fast)
Eden uses `selectinload` strategy by default when you call `.prefetch()`.

```python
# Query 1 & 2: Fetches all employees and all their companies in 2 bulk queries
employees = await Employee.query().prefetch("company").all()

for emp in employees:
    # No extra database hits!
    print(emp.company.name)
```

### Nested Prefetching
Use dot notation to load deep relationships.
```python
# Load Project -> Client -> AccountManager
projects = await Project.query().prefetch("client.account_manager").all()
```

---

## Recursive Relationships

Useful for categories, folder structures, or "Following" systems.

```python
class Category(Model):
    __tablename__ = "categories"
    name: Mapped[str] = f()
    parent_id: Mapped[int] = f(foreign_key="categories.id", nullable=True)
    
    parent: Mapped["Category"] = relationship(remote_side=[id])
    subcategories: Mapped[List["Category"]] = relationship()
```

---

**Next Steps**: [Transactions & Atomicity](orm-transactions.md)
