import pytest
from pydantic import BaseModel
from eden.forms import BaseForm, Schema, field
from eden.context import context_manager
from starlette.requests import Request
from starlette.datastructures import Headers

class SimpleSchema(BaseModel):
    name: str = field(label="Name")

@pytest.mark.asyncio
async def test_xss_vulnerability():
    # Attempt to inject HTML/JS through field value
    unsafe_value = '"><script>alert("xss")</script>'
    form = BaseForm(schema=SimpleSchema, data={"name": unsafe_value})
    
    rendered = str(form["name"].render())
    # If vulnerable, the unsafe value will be present unescaped
    # Specifically, the ">" should be escaped to &quot;&gt; or similar if it's inside an attribute
    # but here it's ending the tag.
    
    print(f"Rendered: {rendered}")
    # A safe implementation should escape the value
    assert '<script>' not in rendered
    assert '&lt;script&gt;' in rendered or 'value="&quot;&gt;&lt;script&gt;' in rendered

@pytest.mark.asyncio
async def test_csrf_inclusion():
    # Mocking request context
    from eden.requests import Request
    from starlette.datastructures import Secret
    
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [],
        "session": {"eden_csrf_token": "test-token-123"}
    }
    request = Request(scope)
    
    async def run_test():
        form = BaseForm(schema=SimpleSchema)
        rendered = str(form.render_all())
        assert 'name="csrf_token"' in rendered
        assert 'value="test-token-123"' in rendered
        return True

    # Run in context
    await context_manager.run_in_context(run_test, request=request)

@pytest.mark.asyncio
async def test_file_upload_size_limit():
    from starlette.datastructures import FormData, UploadFile
    import io
    
    class SmallSchema(BaseModel):
        title: str

    limit = 1024 # 1KB
    
    class LimitedForm(BaseForm):
        MAX_UPLOAD_SIZE = limit

    large_content = b"0" * (limit + 1)
    
    class MockRequest:
        def __init__(self):
            self.headers = Headers({"content-type": "multipart/form-data"})
        async def form(self):
            upload_file = UploadFile(filename="too_large.txt", file=io.BytesIO(large_content), size=len(large_content))
            return FormData([("title", "large"), ("file", upload_file)])

    request = MockRequest()
    
    with pytest.raises(ValueError, match="exceeds maximum upload size"):
        await LimitedForm.from_multipart(SmallSchema, request)

def test_new_widgets():
    class WidgetSchema(BaseModel):
        check: bool = field(widget="checkbox")
        color: str = field(widget="color")
        status: str = field(widget="radio", choices=[("a", "Active"), ("i", "Inactive")])

    form = BaseForm(schema=WidgetSchema, data={"check": True, "color": "#ff0000", "status": "a"})
    
    assert 'type="checkbox"' in str(form["check"].render())
    assert 'checked="checked"' in str(form["check"].render())
    assert 'type="color"' in str(form["color"].render())
    assert 'value="#ff0000"' in str(form["color"].render())
    assert 'type="radio"' in str(form["status"].render())
    assert 'value="a"' in str(form["status"].render())
    assert 'checked="checked"' in str(form["status"].render())

def test_validation_groups():
    class GroupSchema(BaseModel):
        f1: str
        f2: str

    form = BaseForm(schema=GroupSchema, data={"f1": "val1"})
    
    # Normally validation fails because f2 is missing
    assert form.is_valid() is False
    assert "f1" not in form.errors
    assert "f2" in form.errors
    
    # Success if we only include f1
    valid = form.is_valid(include=["f1"])
    if not valid:
        print(f"Errors: {form.errors}")
    assert valid is True
    
    # Success if we exclude f2
    assert form.is_valid(exclude=["f2"]) is True
