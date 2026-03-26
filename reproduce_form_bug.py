from eden.forms import Schema
import pydantic
print(f"Pydantic version: {pydantic.__version__}")

class LoginSchema(Schema):
    email: str
    password: str

print(f"LoginSchema annotations: {LoginSchema.__annotations__}")
try:
    print(f"LoginSchema model_fields: {LoginSchema.model_fields}")
except AttributeError:
    print("LoginSchema has no model_fields")

form = LoginSchema.as_form({"email": "a@b.com", "password": "123"})
valid = form.is_valid()
print(f"Form is valid: {valid}")
if not valid:
    print(f"Errors: {form.errors}")
else:
    print(f"Model instance: {form.model_instance}")
    if form.model_instance:
         print(f"Email: {getattr(form.model_instance, 'email', 'MISSING')}")
         print(f"Attributes: {dir(form.model_instance)}")
