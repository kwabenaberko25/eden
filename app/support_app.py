import sys
import os
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from eden import Eden, Route, admin_site
from eden.admin.models import SupportTicket, TicketMessage
from eden.auth.models import User
from eden.db import init_db
import asyncio

# Create the Eden app
app = Eden(debug=True)
db = init_db("sqlite+aiosqlite:///eden.db", app=app)

@app.route("/support", methods=["GET"])
async def support_demo(request):
    return await app.render("support_demo.html", {"request": request})

# Register admin
app.include_router(admin_site.build_router())

async def setup_db():
    # Canonical way to initialize schema in Eden
    await db.connect(create_tables=True)
    
    import uuid
    DEMO_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
    
    # Create a demo user if it doesn't exist
    async with db.session() as session:
        user = await session.get(User, DEMO_USER_ID)
        if not user:
            user = User(
                id=DEMO_USER_ID,
                username="demo_user",
                email="demo@eden-framework.dev",
                is_superuser=True,
                password_hash="demo_password" # In real app use set_password
            )
            session.add(user)
            await session.commit()
            print(f"Demo user created with ID: {DEMO_USER_ID}")

if __name__ == "__main__":
    import uvicorn
    
    # Run setup
    asyncio.run(setup_db())
    
    uvicorn.run(app, host="127.0.0.1", port=8001)
