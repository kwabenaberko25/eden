
import sys
import os
import asyncio
from markupsafe import Markup

# Add project root to path and set working directory
project_root = os.path.dirname(os.path.abspath(__file__))
os.chdir(project_root)
sys.path.append(project_root)

from eden.app import Eden

async def debug():
    app = Eden(title="Eden Premium Showcase")
    
    # Mock data for the components
    stats = [
        {"label": "Total Revenue", "value": "$124,500", "change": "+14.2%", "icon": "payments", "progress": 75},
        {"label": "Active Users", "value": "12,402", "change": "+5.1%", "icon": "group", "progress": 40},
        {"label": "Server Load", "value": "24%", "change": "-2.0%", "icon": "speed", "progress": 24},
    ]
    
    recent_activity = [
        {"id": 1, "user": "Alex Rivers", "action": "Created Project", "time": "2 mins ago", "status": "Finalizing"},
        {"id": 2, "user": "Sarah Chen", "action": "Updated Billing", "time": "15 mins ago", "status": "Complete"},
        {"id": 3, "user": "Mike Vance", "action": "Deployed App", "time": "1 hour ago", "status": "In Progress"},
    ]
    
    # We need to manually set up the request context since we're not in a real request
    from starlette.requests import Request
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [],
    }
    request = Request(scope)
    
    # Force the template engine to use our mock request
    from eden.context import set_request
    set_request(request)
    
    print("--- RENDERING SHOWCASE ---")
    response = app.render("showcase.html", stats=stats, activity=recent_activity)
    
    # response is a Starlette TemplateResponse
    # We need to render it to string
    body = response.body.decode()
    
    print("--- OUTPUT SAVED TO debug_output.html ---")
    with open("debug_output.html", "w", encoding="utf-8") as f:
        f.write(body)

if __name__ == "__main__":
    asyncio.run(debug())
