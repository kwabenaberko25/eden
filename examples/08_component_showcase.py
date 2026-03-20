import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from eden.app import Eden
from eden.routing import Router
from eden.responses import HtmlResponse

app = Eden(title="Eden Premium Showcase")

@app.get("/")
async def showcase():
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
    
    return app.render("showcase.html", stats=stats, activity=recent_activity)

if __name__ == "__main__":
    app.run()
