
from eden.app import Eden
from starlette.testclient import TestClient
import os
import shutil

def test_user_mistake():
    # Setup template dir
    template_dir = os.path.abspath("templates_mistake")
    if os.path.exists(template_dir):
        shutil.rmtree(template_dir)
    os.makedirs(template_dir, exist_ok=True)
    
    # User's mistake: removed @ from @for
    # Before: @for (emp in workers) { {{ emp }} }
    # After: for (emp in workers) { {{ emp }} }
    template_content = """
    <h1>Employee List</h1>
    for (emp in workers) {
        <p>{{ emp }}</p>
    }
    """
    with open(os.path.join(template_dir, "mistake.html"), "w") as f:
        f.write(template_content)
    
    app = Eden(debug=True)
    app.template_dir = template_dir
    from jinja2 import StrictUndefined
    app.templates.env.undefined = StrictUndefined

    
    @app.route("/")
    async def index(request):
        # We pass workers, but emp will still be undefined because the loop isn't a directive
        return app.render("mistake.html", {"workers": ["Alice", "Bob"]})
    
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/")
    
    # Print the response to see what's being shown
    with open("mistake_output.html", "w", encoding="utf-8") as f:
        f.write(response.text)
    
    print(f"Status: {response.status_code}")
    if "Undefined Variable" in response.text:
        print("Caught Undefined Variable error!")
    
    # Check if 'emp' is mentioned in the error
    if "'emp' is undefined" in response.text:
        print("Specifically identified 'emp' as undefined.")

    # Check for our new suggestion
    if "@for" in response.text and "forget to add the" in response.text:
        print("FOUND HEURISTIC SUGGESTION: Mentioned forgetting '@' for @for.")
    else:
        print("HEURISTIC SUGGESTION NOT FOUND in debug output.")

if __name__ == "__main__":
    test_user_mistake()
