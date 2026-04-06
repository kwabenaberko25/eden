Searched for "TODO"
Searched for "TODO"

Based on the actual source code we have right now—and general reality checks around putting async Python ORMs into production—there are still a few **architectural gaps** that you will need to address to ensure Eden operates flawlessly at scale. 

While the fundamental architecture (P0 and P1) is stable, a resilient production application will eventually run into these 4 specific boundaries:

### 1. The "Background Tasks" Crash (Context Bleed)
Right now, Eden binds the database session to the HTTP request lifecycle. If you try to fire off an asynchronous task to run in the background (e.g., sending a welcome email logging to the DB) using standard tools like Starlette's `BackgroundTasks`, **it will crash**. 
- **The Issue**: Background tasks execute *after* the HTTP response is returned. By that point, the Eden framework middleware has already committed and closed that specific database session. If your background task tries to access the DB using the implied session context, it will hit an un-bound session error. 
- **The Fix Required**: You will need to implement a dedicated `db.background_transaction()` context manager that safely spawns an entirely new, parallel DB dependency detached from the main request tree.

### 2. Missing "Detached Instance / Lazy-Loading" Protections
In `eden/db/session.py`, we explicitly instantiate `async_sessionmaker(..., expire_on_commit=False)`. This is generally good because your Python objects don't immediately "forget" their data after the transaction ends.
- **The Issue**: Because it is `async`, SQLAlchemy strictly disables implicit "Lazy Loading" of related tables (Because lazy loading blocks the I/O thread). If you query a `Tenant`, close the session, and *then* try to access `tenant.users` later in your code, the framework will throw a `MissingGreenletError`.
- **The Fix Required**: Developers must be strictly trained to use `.options(selectinload(Model.relation))` during the initial `.filter()` phase for any nested data they need.

### 3. Orphaned PostgreSQL Schemas (Data Bloat)
In `eden/tenancy/models.py`, we built a very robust `provision_schema` method that handles Alembic schema creation beautifully when a new tenant signs up.
- **The Issue**: There is currently no opposite `drop_schema` functionality implemented. If a `Tenant` model is hard-deleted from the database, the physical PostgreSQL schema (and all its gigabytes of relational tables) remains behind as orphaned, wasted space.
- **The Fix Required**: We should either bind a listener to `Tenant.delete()` that natively executes a `DROP SCHEMA "{schema}" CASCADE`, or enforce a strict Soft-Delete policy for Tenants via `SoftDeleteMixin` so data is never actually detached, just hidden.

### 4. Hardcoded Connection Pool Limits
If you look at `eden/db/session.py`, if a developer doesn't pass explicit limits, it forces a baseline:
```python
kwargs.setdefault("pool_size", 10)
kwargs.setdefault("max_overflow", 20)
```
- **The Issue**: If you deploy this to production using 4 highly-concurrent Uvicorn workers (e.g., on a basic 2-core cloud VPS), each worker spins up 30 potential connections (10 + 20 overflow). That’s **120 concurrent connections**, instantly exhausting the default database connection limits of managed providers like Supabase or AWS RDS (which often default to ~60-100 without PgBouncer).
- **The Fix Required**: The `Database` setup needs to proactively strip these hardcoded limits out and exclusively pull `DB_POOL_SIZE` boundaries from the `.env` configuration, keeping the developer fully aware of connection saturation dynamically. 

None of these mean Eden is broken—they are standard hurdles of building robust async ORM applications. But actively designing mitigations for these four spots should absolutely be the focus of the next maturation phase.