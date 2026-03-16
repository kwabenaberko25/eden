# Transactions & Atomicity 🛡️

Eden provides robust tools for ensuring data integrity through atomic operations.

## The `@atomic` Decorator

The simplest way to wrap a controller or service method in a transaction. If an exception is raised, the entire operation is rolled back.

```python
from eden.db import atomic

@app.post("/checkout")
@atomic
async def process_checkout(request):
    # If any of these fail, everything is rolled back
    order = await Order.create(status="processing")
    await Inventory.adjust(items=request.json["items"])
    await Payment.record(order=order)
    
    return json({"status": "success"})
```

---

## Context Manager Usage

For fine-grained control, use the `db.session()` context manager.

```python
from eden.db import get_db

async def transfer_credits(sender_id, receiver_id, amount):
    db = get_db()
    
    async with db.session() as session:
        sender = await User.get(sender_id, session=session)
        receiver = await User.get(receiver_id, session=session)
        
        if sender.credits < amount:
            raise ValueError("Insufficient credits")
            
        sender.credits -= amount
        receiver.credits += amount
        
        # Saves are buffered in the session
        await sender.save(session=session)
        await receiver.save(session=session)
        
        # Transaction commits automatically at the end of 'async with'
```

---

## Savepoints (Nested Transactions)

Use `session.begin_nested()` to create a savepoint. This allows you to roll back a specific part of a transaction without losing the whole thing.

```python
async with db.session() as session:
    # Main transaction
    await MainRecord.create(data="main")
    
    try:
        async with session.begin_nested():
            # This part can fail independently
            await OptionalLog.create(msg="attempting...")
            raise RuntimeError("Sub-task failed")
    except RuntimeError:
        # Savepoint rolled back, but 'MainRecord' is still intact
        print("Optional task failed, but main task continues")
        
    # MainRecord will be committed here
```

---

## Implicit Session Handling

Eden models are "session-aware". When you call a method like `.save()` or `.update()` within an active session context (like under an `@atomic` decorator), Eden automatically uses that session.

### The Lifecycle
1. **Request Starts**: Middleware prepares a session if needed.
2. **Logic Executes**: `Model.get()` or `Model.filter()` finds the active session.
3. **Commit/Rollback**: Handled automatically by the context manager.

---

## Best Practices

1. **Keep Transactions Short**: Don't perform long-running blocking operations (like external API calls or large file reads) inside an atomic block.
2. **Order of Operations**: Perform logic/validation *before* starting the transaction if possible.
3. **Explicit Sessions**: For complex service layers, it's often better to pass the `session` object explicitly to ensure all model calls stay in the same transaction.

```python
# Service Layer Pattern
class BillingService:
    async def bill_subscriber(self, user, amount, session=None):
        # Use provided session or model default
        invoice = await Invoice.create(user=user, amount=amount, session=session)
        return invoice
```

---

**Next Steps**: [Migrations](orm-migrations.md)
