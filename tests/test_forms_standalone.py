import sys
from eden.forms import Schema, BaseForm

class LoginSchema(Schema):
    email: str
    password: str

form = LoginSchema.as_form({"email": "a@b.com", "password": "123"})
valid = form.is_valid()
print(f"Valid: {valid}")
if valid:
     print(f"Email: {form.model_instance.email}")

class TestSchema(Schema):
     name: str
     age: int

form2 = BaseForm(schema=TestSchema, data={"name": "X", "age": "25"})
fields = list(form2)
print(f"Fields: {[f.name for f in fields]}")
assert len(fields) == 2
