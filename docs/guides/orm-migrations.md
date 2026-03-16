# Database Migrations 🏗️

Eden uses **Alembic** under the hood to provide a robust, version-controlled migration system that evolves your schema as your models change.

## The Workflow

The standard cycle for database changes in Eden:
1. **Change Models**: Update your inheriting `Model` classes in Python.
2. **Generate Script**: Create a new migration file with `eden migrate create`.
3. **Review**: Check the generated Python file in your `migrations/` folder.
4. **Apply**: Execute `eden migrate upgrade head`.

---

## CLI Reference

| Command | Description |
| :--- | :--- |
| `eden migrate create "Added bio to user"` | Auto-detect model changes and create a script. |
| `eden migrate upgrade head` | Apply all pending migrations to the database. |
| `eden migrate upgrade +1` | Apply only the next migration. |
| `eden migrate downgrade base` | Revert all migrations (Wipes Schema!). |
| `eden migrate downgrade -1` | Revert the last applied migration. |
| `eden migrate history` | List all available and applied migrations. |

---

## Detailed Example: Adding a New Field

### 1. Update your Model
```python
class User(Model):
    name: str = f()
    phone_number: str = f(nullable=True) # New field
```

### 2. Generate Migration
```bash
eden migrate create "Add phone to user"
```
Eden will output: `Generating /migrations/versions/a1b2c3d4e5f6_add_phone_to_user.py`

### 3. Review the Script
The generated file looks like this:
```python
def upgrade():
    op.add_column('users', sa.Column('phone_number', sa.String(), nullable=True))

def downgrade():
    op.drop_column('users', 'phone_number')
```

### 4. Apply
```bash
eden migrate upgrade head
```

---

## Advanced Scenarios

### Data Migrations
Sometimes you need to migrate the data itself (e.g., converting a single 'name' field to 'first_name' and 'last_name'). You can use the `op.execute()` method in your migration script.

```python
def upgrade():
    # 1. Add new columns
    op.add_column('users', sa.Column('first_name', sa.String()))
    
    # 2. Migrate data with raw SQL
    op.execute("UPDATE users SET first_name = split_part(name, ' ', 1)")
    
    # 3. Handle old column
    op.drop_column('users', 'name')
```

### Drift Detection
Eden can detect when your production database schema doesn't match your models. Run `eden migrate status` to see if your database is "dirty" compared to your codebase.

### Squashing Migrations
As your project grows, you might end up with hundreds of small migrations. You can "squash" them into a single initial file by clearing your `migrations/versions` folder and running `eden migrate create "initial" --squash`.

---

## Best Practices

- **Never Delete Migrations**: If you made a mistake, create a new "fix" migration rather than editing an old one.
- **Check-in Scripts**: Always commit the `migrations/` directory to your version control system.
- **production-safe**: Always run `downgrade` tests locally before deploying to production.
- **Constraints**: Be careful when adding `NOT NULL` constraints to existing tables with data; either provide a default or do it in two steps (add nullable -> fill data -> set not null).

---

**Next Steps**: [Authentication Overview](auth.md)
