import asyncio
from eden.templating import EdenTemplates
from eden.forms import Schema, f
from pydantic import EmailStr

print("\n--- Starting Eden Templating & Forms Audit ---")

# --- TEST 1: Templating Engine Initialization ---
print("\n[Test 1] Templating Engine...")

templates = EdenTemplates(directory=".")

# Check filters
filters = templates.env.filters
required_filters = [
    "time_ago",
    "money",
    "class_names",
    "add_class",
    "truncate",
    "slugify",
    "json_encode",
    "pluralize",
    "mask",
    "file_size",
]

missing = [f for f in required_filters if f not in filters]
if missing:
    print(f"[FAIL] Missing filters: {missing}")
else:
    print("[PASS] All core filters present.")

# Check globals
globals = templates.env.globals
required_globals = ["now", "is_active", "eden_head", "eden_scripts", "old", "vite"]
missing_g = [g for g in required_globals if g not in globals]
if missing_g:
    print(f"[FAIL] Missing globals: {missing_g}")
else:
    print("[PASS] All core globals present.")

# --- TEST 2: Forms & Schema ---
print("\n[Test 2] Forms & Schema...")


class LoginSchema(Schema):
    email: EmailStr = f(widget="email")
    password: str = f(min_length=8, widget="password")


# Create form
form = LoginSchema.as_form(data={"email": "test@example.com", "password": "password123"})

if form.is_valid():
    print("[PASS] Form validation passed.")
else:
    print(f"[FAIL] Form validation failed: {form.errors}")

# Test field access
email_field = form["email"]
print(f"   Debug: field attributes: {email_field.attributes}")
if email_field.widget == "email":
    print("[PASS] Field widget correct.")
else:
    print(f"[FAIL] Field widget incorrect: {email_field.widget} (expected 'email')")

if email_field.field_type == "email":
    print("[PASS] Field type correct.")
else:
    print(f"[FAIL] Field type incorrect: {email_field.field_type}")

# Test rendering
rendered = email_field.render()
if "input" in rendered and "email" in rendered:
    print("[PASS] Field renders correctly.")
else:
    print(f"[FAIL] Field render issue: {rendered[:100]}")

# --- TEST 3: Component Rendering ---
print("\n[Test 3] Component System...")

# Check if accordion component is registered
from eden.components import get_component

acc = get_component("accordion")
if acc:
    print("[PASS] Accordion component registered.")
else:
    print("[FAIL] Accordion component not found.")

# --- TEST 4: Directive Parsing (Simulated) ---
print("\n[Test 4] Template Directives...")

# We can't easily test full rendering without a template file,
# but we can check that the extension loads.
# The EdenDirectivesExtension is added in EdenTemplates.__init__

# Just verify the class exists
from eden.templating import EdenDirectivesExtension

print("[PASS] EdenDirectivesExtension loaded.")

print("\n--- Audit Complete ---")
