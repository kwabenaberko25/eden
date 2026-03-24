import pytest
from pydantic import BaseModel, Field
from eden.forms import BaseForm

class UserSchema(BaseModel):
    name: str = Field(..., min_length=2)
    email: str = Field(..., pattern=r".+@.+\..+")

def test_form_validation_groups_missing_model_instance():
    """
    Test that if a field is required but not in scope, is_valid returns True 
    but model_instance is NOT None and contains the validated data.
    """
    # Case 1: Partial data (only name)
    data = {"name": "Alice"}
    form = BaseForm(schema=UserSchema, data=data)
    
    # We only care about name
    valid = form.is_valid(include=["name"])
    
    assert valid is True, "Form should be valid when only checking 'name'"
    assert form.model_instance is not None, "model_instance should NOT be None"
    assert form.model_instance.name == "Alice"
    # email should be None or default if we used model_construct
    # currently it fails in the codebase because it sets email=None and pydantic fails validation

if __name__ == "__main__":
    pytest.main([__file__])
