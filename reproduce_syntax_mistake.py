import os
from eden.app import Eden
from starlette.testclient import TestClient

def test_syntax_mistake():
    # Setup template dir
    template_dir = os.path.abspath("templates_mistake")
    os.makedirs(template_dir, exist_ok=True)
    
    # Missing opening brace for @for
    template_content = """
    <!DOCTYPE html>
    <html>
    <body>
        @for (emp in workers)
            <p>{{ emp.name }}</p>
        }
    </body>
    </html>
    """
    with open(os.path.join(template_dir, "syntax_mistake.html"), "w") as f:
        f.write(template_content)

    app = Eden(debug=True)
    app.template_dir = template_dir
    
    @app.route("/")
    def brace_mistake(request):
        workers = [{"name": "Alice"}]
        return app.render("syntax_mistake.html", {"workers": workers})

    @app.route("/syntax")
    def jinja_mistake(request):
        # Create Jinja-style template on the fly
        with open(os.path.join(template_dir, "syntax_jinja.html"), "w") as f:
            f.write("""
            {% for emp in workers
                <p>{{ emp.name }}</p>
            {% endfor %}
            """)
        return app.render("syntax_jinja.html", {"workers": []})

    client = TestClient(app, raise_server_exceptions=False)
    print("Sending request to trigger syntax framework error...")
    
    # Case 1: UndefinedError from missing brace
    response = client.get("/")
    print(f"Status (/): {response.status_code}")
    
    with open("syntax_mistake_output.html", "w", encoding="utf-8") as f:
        f.write(response.text)
        
    if "missing an opening <code>{</code>" in response.text:
        print("PASSED: Found suggestion for missing '{'.")
    else:
        print("FAILED: Did not find suggestion for missing '{'.")

    # Case 2: TemplateSyntaxError from Jinja blocks
    print("Testing /syntax (Jinja-style error)...")
    response = client.get("/syntax")
    print(f"Status (/syntax): {response.status_code}")
    
    with open("syntax_error_output.html", "w", encoding="utf-8") as f:
        f.write(response.text)
        
    if "Eden uses a modern" in response.text:
        print("PASSED: Found suggestion for Jinja-style syntax.")
    else:
        # Check if it was caught as a generic exception
        if "TemplateSyntaxError" in response.text:
            print("INFO: TemplateSyntaxError detected, but heuristic didn't trigger.")
        else:
            print("FAILED: TemplateSyntaxError not even in output.")

if __name__ == "__main__":
    test_syntax_mistake()
