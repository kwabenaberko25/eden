import asyncio
import uuid
from typing import List, Optional
from sqlalchemy.orm import Mapped
from sqlalchemy import String, Text, Integer, Boolean, Enum
from eden.db import Model, f, Database
from eden.forms import BaseForm

class User(Model):
    __tablename__ = "users_test"
    name: Mapped[str] = f(max_length=100, label="Full Name")
    email: Mapped[str] = f(widget="email")
    bio: Mapped[Optional[str]] = f(type_=Text, help_text="A bit about you")
    age: Mapped[Optional[int]] = f(type_=Integer, info={"min": 18, "max": 120})
    role: Mapped[str] = f(type_=Enum("admin", "user", name="user_roles"), default="user")
    is_active: Mapped[bool] = f(default=True)

async def test_as_form():
    db = Database("sqlite+aiosqlite:///:memory:")
    await db.connect()
    
    # Generate form
    form = User.as_form()
    
    print("--- Form Fields ---")
    for name in form.schema.model_fields:
        field = form[name]
        print(f"Field: {name}")
        print(f"  Label: {field.label}")
        print(f"  Widget: {field.widget}")
        print(f"  Required: {field.required}")
        print(f"  Attributes: {field.attributes}")
        print(f"  HTML: {field.render()}")
        print()

    await db.disconnect()

if __name__ == "__main__":
    asyncio.run(test_as_form())
