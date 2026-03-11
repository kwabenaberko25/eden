from sqlalchemy import inspect
from tmp_test_forms import User

print("Column Properties:")
for name, col in User.__table__.columns.items():
    has_def = col.default is not None or col.server_default is not None
    print(f"  {name}: nullable={col.nullable}, has_default={has_def}, default={col.default}")
