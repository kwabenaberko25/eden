"""
test_minimal - Web Application
Built with Eden Framework 🌿
"""

from eden import Eden
import os

# Initialize application
app = Eden(
    title="test_minimal",
    version="1.0.0",
    secret_key=os.getenv("SECRET_KEY", "change-me-in-production"),
    debug=os.getenv("DEBUG", "true").lower() == "true"
)

# Database configuration
app.state.database_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///db.sqlite3")

# Middleware stack (order matters!)
app.add_middleware("security")        # Security headers first
app.add_middleware("session", secret_key=app.secret_key)
app.add_middleware("csrf")            # CSRF requires session
app.add_middleware("gzip")            # Compression
app.add_middleware("cors", allow_origins=["*"])

@app.get("/")
async def index():
    """Welcome endpoint."""
    return {"message": "Welcome to test_minimal! 🌿"}

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}

if __name__ == "__main__":
    app.run()
