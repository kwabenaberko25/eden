# HTMX Integration 🎯

HTMX enables interactive web pages without writing JavaScript. It lets you access AJAX, WebSockets, and more directly in HTML.

## Getting Started

Include HTMX in your template:

```html
<script src=\"https://unpkg.com/htmx.org@1.9.10\"></script>
```

## Basic Usage

### Load Content on Click

```html
<!-- Click loads /api/notifications and inserts into #notifications -->
<div id=\"notifications\">
    Loading...
</div>

<button hx-get=\"/api/notifications\" hx-target=\"#notifications\">
    Load Notifications
</button>
```

### Form Submission

```html
<!-- Submit form via AJAX -->
<form hx-post=\"/users\" hx-validate>
    <input name=\"email\" type=\"email\" required>
    <input name=\"name\" type=\"text\" required>
    <button type=\"submit\">Create User</button>
</form>
```

## Eden Integration

```python
@app.get(\"/api/notifications\")
async def get_notifications(request):
    \"\"\"Return HTML snippet for HTMX.\"\"\"
    notifications = await Notification.filter(
        user_id=request.user.id,
        read=False
    ).all()
    
    html = \"<ul>\"
    for notif in notifications:
        html += f\"<li>{notif.message}</li>\"
    html += \"</ul>\"
    
    return html  # HTMX will insert this directly

@app.post(\"/users\")
async def create_user(request):
    \"\"\"Handle HTMX form submission.\"\"\"
    data = await request.form()
    
    try:
        user = await User.create(
            email=data[\"email\"],
            name=data[\"name\"]
        )
        # Return success HTML snippet
        return f\"<p>User {user.name} created!</p>\"
    except ValidationError as e:
        # Return error HTML
        return f\"<p class='error'>{e}</p>\", 400
```

## Advanced Features

### Pagination with HTMX

```html
<div id=\"posts\">
    <!-- Initial page of posts loaded here -->
</div>

<button 
    hx-get=\"/posts?page=2\" 
    hx-target=\"#posts\" 
    hx-swap=\"beforeend\"
    hx-trigger=\"revealed\"
    >
    Load More
</button>
```

### Real-Time Updates with WebSockets

```python
# Combine HTMX with WebSocket for real-time updates
@app.websocket(\"/ws/live-feed\")
async def live_feed(websocket):
    await websocket.accept()
    
    while True:
        new_posts = await Post.filter(created_at__gt=time.time() - 5).all()
        
        html = \"\"
        for post in new_posts:
            html += f\"\"\"
            <div class='post'>
                <h3>{post.title}</h3>
                <p>{post.content}</p>
            </div>
            \"\"\"
        
        await websocket.send_html(html)
```

## Best Practices

- ✅ Return HTML snippets from your routes
- ✅ Use CSRF tokens with POST/PUT/DELETE requests
- ✅ Handle validation errors gracefully
- ✅ Test with different network conditions
- ✅ Provide fallbacks for users without JavaScript
