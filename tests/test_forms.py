import pytest
from pydantic import BaseModel, EmailStr
from eden.forms import BaseForm, FormField

class UserSchema(BaseModel):
    username: str
    email: EmailStr
    age: int

def test_form_validation():
    form = BaseForm(schema=UserSchema, data={"username": "eden", "email": "invalid", "age": "abc"})
    
    assert form.is_valid() is False
    assert "email" in form.errors
    assert "age" in form.errors
    
    # Check field rendering
    email_field = form["email"]
    assert email_field.name == "email"
    assert "invalid" in str(email_field.render())
    assert "border-red-500" in str(email_field.render())
    
    # Check label rendering
    assert "Email" in str(email_field.render_label())

def test_form_success():
    form = BaseForm(schema=UserSchema, data={"username": "eden", "email": "test@example.com", "age": 25})
    assert form.is_valid() is True
    assert form.model_instance.username == "eden"
    assert form.model_instance.age == 25

def test_form_from_model():
    class MockModel:
        __pydantic_model__ = UserSchema
        def __init__(self):
            self.username = "model_user"
            self.email = "model@test.com"
            self.age = 30
        def to_dict(self):
            return {"username": self.username, "email": self.email, "age": self.age}
            
    instance = MockModel()
    form = BaseForm.from_model(instance)
    
    assert form.data["username"] == "model_user"
    assert form.data["age"] == 30
    assert form.is_valid() is True

def test_render_all():
    form = BaseForm(schema=UserSchema)
    html = str(form.render_all())
    
    assert 'name="username"' in html
    assert 'name="email"' in html
    assert 'name="age"' in html
    assert '<label' in html

@pytest.mark.asyncio
async def test_form_from_multipart():
    from starlette.datastructures import FormData, UploadFile
    import io

    class UploadSchema(BaseModel):
        title: str

    file_content = b"test file content"
    upload_file = UploadFile(filename="test.txt", file=io.BytesIO(file_content), size=len(file_content), headers={"content-type": "text/plain"})
    
    class MockRequest:
        async def form(self):
            return FormData([("title", "My File"), ("document", upload_file)])

    request = MockRequest()
    
    form = await BaseForm.from_multipart(UploadSchema, request)
    assert form.is_valid() is True
    assert form.data["title"] == "My File"
    
    assert "document" in form.files
    uploaded_file = form.files["document"]
    assert uploaded_file.filename == "test.txt"
    assert uploaded_file.size == len(file_content)
    assert uploaded_file.content_type == "text/plain"
    assert uploaded_file.data == file_content
