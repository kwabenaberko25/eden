from sqlalchemy.orm import mapped_column
mc = mapped_column(info={"test": True})
print(f"hasattr column: {hasattr(mc, 'column')}")
try:
    print(f"col: {mc.column}")
except Exception as e:
    print(f"col error: {e}")
