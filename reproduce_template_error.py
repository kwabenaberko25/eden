import os
import threading
import time
import requests
import uvicorn
from eden.app import Eden
from eden.responses import HtmlResponse
from eden import render_template

# Create app
app = Eden(debug=True)

# Create a broken template
TEMPLATES_DIR = os.path.join(os.getcwd(), "templates")
os.makedirs(TEMPLATES_DIR, exist_ok=True)

broken_template_path = os.path.join(TEMPLATES_DIR, "broken.html")
# Missing closing brace for a section
with open(broken_template_path, "w") as f:
    f.write("""
    <h1>Hello {{ name }}</h1>
    {% section "content" %}
        <p>This section is broken because it doesn't close correctly.
    {% endsection
    """)

@app.get("/")
def home(request):
    return render_template("broken.html", name="Eden")

@app.get("/exception")
def backend_error(request):
    # This will raise a NameError
    return some_undefined_variable

def run_server():
    uvicorn.run(app, host="127.0.0.1", port=8001, log_level="error")

def test_debug_page():
    time.sleep(2)  # Wait for server to start
    
    print("Requesting broken template...")
    try:
        response = requests.get("http://127.0.0.1:8001/")
        print(f"Status: {response.status_code}")
        if response.status_code == 500 and ("Eden" in response.text or "CRITICAL ERROR" in response.text):
            print("✅ Successfully caught template syntax error and rendered premium debug page.")
        else:
            print("❌ Failed to render premium debug page for template error.")
    except Exception as e:
        print(f"Error: {e}")

    print("\nRequesting backend exception...")
    try:
        response = requests.get("http://127.0.0.1:8001/exception")
        print(f"Status: {response.status_code}")
        if response.status_code == 500 and ("Eden" in response.text or "CRITICAL ERROR" in response.text):
            print("✅ Successfully caught backend exception and rendered premium debug page.")
            if "some_undefined_variable" in response.text:
                print("✅ Debug page correctly displays the exception details (NameError).")
        else:
            print("❌ Failed to render premium debug page for backend exception.")
    except Exception as e:
        print(f"Error: {e}")

    print("\nTest finished.")

if __name__ == "__main__":
    # Start server in a thread
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    test_debug_page()
