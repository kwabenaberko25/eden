import asyncio
import uuid
from typing import Optional
from pydantic import BaseModel
from eden import Schema, field, init_migrations as init_db # init_db is often aliased or in eden.db
from eden.db import Model, f, init_db
from eden.forms import ModelForm, BaseForm, EmailStr
from eden.requests import Request
from starlette.datastructures import Headers

# 1. Mock DB Model
class User(Model):
    __tablename__ = "users_test"
    id: uuid.UUID = f(primary_key=True, default=uuid.uuid4)
    username: str = f(max_length=50, unique=True)
    email: str = f(max_length=255)

# 2. Schema Definition
class RegistrationSchema(Schema):
    username: str = field(label="User Name", min_length=3)
    email: EmailStr = field(label="Email Address", widget="email")
    password: str = field(min_length=8, widget="password")

# 3. ModelForm Definition
class UserForm(ModelForm):
    class Meta:
        model = User
        fields = ["username", "email"]

async def test_form_logic():
    print("Testing Eden Form System...")
    
    # Initialize DB (InMemory for test)
    db = init_db("sqlite+aiosqlite:///:memory:")
    await db.connect(create_tables=True)
    
    # --- Test 1: Schema as Form ---
    print("\n[Test 1] Schema.as_form()...")
    data = {"username": "ed", "email": "invalid"}
    form = RegistrationSchema.as_form(data)
    
    is_valid = form.is_valid()
    print(f"Is Valid (should be False): {is_valid}")
    print(f"Errors: {form.errors}")
    
    assert not is_valid
    assert "username" in form.errors
    assert "email" in form.errors
    
    # --- Test 2: Field Rendering ---
    print("\n[Test 2] Field Rendering...")
    username_field = form["username"]
    print(f"Label: {username_field.label}")
    render_html = username_field.render(class_="form-control")
    print(f"Rendered HTML (partial): {render_html[:50]}...")
    assert 'name="username"' in render_html
    assert 'value="ed"' in render_html
    
    # --- Test 3: ModelForm Save ---
    print("\n[Test 3] ModelForm Save...")
    user_data = {"username": "eden_user", "email": "user@eden-framework.dev"}
    form = UserForm(data=user_data)
    
    if form.is_valid():
        user_instance = await form.save()
        print(f"User Saved: {user_instance.username} (ID: {user_instance.id})")
        assert user_instance.username == "eden_user"
        
        # Verify in DB
        fetched = await User.query().filter(username="eden_user").first()
        assert fetched is not None
        assert fetched.email == "user@eden-framework.dev"
    else:
        print(f"Form errors: {form.errors}")
        assert False, "Form should be valid"

    print("\n[SUCCESS] Form system verification complete.")

if __name__ == "__main__":
    asyncio.run(test_form_logic())
