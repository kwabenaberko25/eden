
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.abspath("."))

from eden.templating.templates import EdenTemplates

# Create a dummy template directory
templates_dir = os.path.join(os.path.abspath("."), "test_templates")
os.makedirs(templates_dir, exist_ok=True)
    
test_tpl = os.path.join(templates_dir, "test_filter.html")
with open(test_tpl, "w") as f:
    f.write("{{ val | json_encode }}")

try:
    templates = EdenTemplates(directory=templates_dir)
    print(f"Filters found: {'json_encode' in templates.env.filters}")
    
    # Try rendering
    from jinja2 import Template
    tpl = templates.get_template("test_filter.html")
    rendered = tpl.render(val={"a": 1})
    print(f"Rendered: {rendered}")
except Exception as e:
    import traceback
    traceback.print_exc()
finally:
    # Cleanup
    if os.path.exists(test_tpl):
        os.remove(test_tpl)
    if os.path.exists(templates_dir):
        os.rmdir(templates_dir)
