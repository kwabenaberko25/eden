# Phase 2: The Data Forge (ORM & Evolution) ⚒️

Data is the lifeblood of **Eden**. In this phase, we will master the **Eden ORM**—a high-performance, asynchronous engine powered by SQLAlchemy 2.0 but optimized for elite developer productivity. This phase now covers both schema definition and evolution.

---

## 🏗️ Connecting to the Core

Before we define our entities, we must establish a link to the persistent storage. Eden supports SQLite (local) and PostgreSQL (production) with the same "Elite" interface.

### 1. Initializing the Database

In your `app.py`, initialize the `Database` manager.

```python
from eden.db import Database

# 🔌 Initialize the local database link
db = Database("sqlite+aiosqlite:///Eden.db")
```

### 2. The Connection Lifecycle

To ensure the database is ready when requests arrive, hook it into Eden's startup event.

```python
from eden import Eden
app = Eden\(debug=True, title="Eden")

@app.on_startup
async def startup_db():
    # 🚀 Ignite the database connection
    await db.connect()

@app.on_shutdown
async def shutdown_db():
    # 💤 Gracefully close the connection
    await db.disconnect()
```

---

## 🧱 Defining Portal Entities

Modify your `models.py` file to define the core entities of the Eden. Eden models use **SQLAlchemy 2.0's Mapped** syntax combined with Eden's field helpers.

### 1. Elite Field Types

Eden provides clean helpers in `eden.db` that return configured `mapped_column` instances.

| Helper | Type | Common Arguments |
| :--- | :--- | :--- |
| `f` | `str` | `max_length`, `unique`, `required` |
| `f` | `int` | `index`, `unique`, `default` |
| `f` | `bool` | `default` |
| `f` | `datetime` | `auto_now`, `auto_now_add` |
| `f` | `uuid.UUID` | `primary_key`, `default_factory` |
| `JSONField` | `dict` | `default` |

### 3. The Zen Helper `f()` 🧘

For the most compact and "Elite" experience, Eden provides the `f()` helper. It intelligently infers types and sets up common metadata for forms and validation.

```python
from eden.db import Model, f

class Sector(Model):
    __tablename__ = "sectors"
    
    # Intelligently inferred from arguments
    name: str = f(max_length=150, required=True, unique=True)
    description: str = f(widget="textarea")
    launch_date: datetime = f(auto_now_add=True)
    capacity: int = f(default=100, min=0, max=500)
```

---

### 2. The Sector Entity (Expanded)

```python
from eden.db import Model, f

class Sector(Model):
    """Persistent storage for Sector metadata."""
    __tablename__ = "sectors"
    
    # Required field (nullable=False)
    name: str = f(max_length=150, required=True, unique=True)
    slug: str = f(max_length=50, required=True, unique=True, index=True)
    
    # Field with default
    is_active: bool = f(default=True)
    
    # Auto-timestamps
    created_at: datetime = f(auto_now_add=True)
    last_sync: datetime = f(auto_now=True)
```

---

## 🔗 Forging Relationships

Eden simplifies relationship management with intelligent late-binding.

### 1. One-to-Many

Suppose every **Sector** has multiple **Drones**.

```python
from eden.db import ForeignKeyField, Relationship

class Drone(Model):
    __tablename__ = "drones"
    
    serial_number: str = f(unique=True)
    # Link to Sector
    sector_id: Mapped[uuid.UUID] = ForeignKeyField("sectors.id", required=True)
    
    # The back-reference
    sector: "Sector" = Relationship("Sector", back_populates="drones")

# Update Sector to include the collection
class Sector(Model):
    # ... previous fields ...
    drones: list["Drone"] = Relationship("Drone", back_populates="sector")
```

### 2. Many-to-Many

For complex systems, use `ManyToManyField`. For example, **Sectors** can have multiple **Security Protocols**.

```python
from eden.db import ManyToManyField

class Protocol(Model):
    __tablename__ = "protocols"
    name: str = f(unique=True)
    
    sectors: list["Sector"] = ManyToManyField("Sector", through="rel_sector_protocols")
```

---

## 🧬 Forge Evolutions (Migrations)

As the Eden grows, use **Forge** to evolve your schema safely.

### 1. Generating a Migration

When you change a model, detect the diff automatically:

```bash
uv run eden db generate -m "Add telemetry fields to sector"
```

### 2. Applying the Change

```bash
uv run eden db migrate
```

---

## ✅ Verification

1. **Verify Connection**: Run `python app.py` and check for `Eden.db`.
2. **Verify Schema**: Run `eden db migrate` and inspect the tables.
3. **Verify Modeling**: Ensure `models.py` imports `Model` and uses `Mapped` consistently.

If all pass, your Data Forge is **100% Verified**. You are ready for **Phase 3: The QuerySet API**.

