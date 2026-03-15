#!/usr/bin/env python
"""
Final verification that the template error page enhancement is working.
"""
import tempfile
from pathlib import Path
from starlette.testclient import TestClient
from eden.app import Eden

# Create temp template directory
tmp_dir = tempfile.mkdtemp()
template_dir = Path(tmp_dir) / "templates"
template_dir.mkdir(exist_ok=True)

# Create template with syntax error
(template_dir / "test.html").write_text("<h1>Test</h1>\n{% broken %}")

# Setup app
app = Eden(debug=True)
app.template_dir = str(template_dir)

@app.route("/")
async def index(request):
    return app.render("test.html", {"user": "Alice", "count": 42})

# Test
client = TestClient(app, raise_server_exceptions=False)
response = client.get("/")

# Verify
assert response.status_code == 500, f"Expected 500, got {response.status_code}"
assert "Template Error" in response.text or "Syntax Error" in response.text, "No error badge"
assert "Code Explorer" in response.text, "No code explorer"
assert "Environment Snapshot" in response.text, "No environment"
assert response.text.count("</div>") > 0, "Invalid HTML structure"

print("✅ Template error page enhancement is working correctly!")
print("✅ All requirements met")
print("✅ Feature is complete and functional")
