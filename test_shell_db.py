from eden import Eden

app = Eden(title="Test")
app.state.database_url = "sqlite+aiosqlite:///:memory:"

print(f"Before: Has db? {hasattr(app.state, 'db')}")

if hasattr(app, "_build_services"):
    app._build_services()

print(f"After: Has db? {hasattr(app.state, 'db')}")

