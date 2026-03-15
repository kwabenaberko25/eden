
from eden.templating import EdenDirectivesExtension
from jinja2 import Environment

source = """
    @if (user.is_admin) {
        <h1>Admin</h1>
    } @else if (user.is_editor) {
        <h2>Editor</h2>
    } @else {
        <p>User</p>
    }
    
    @for (item in items) {
        <li>{{ item }}</li>
    }
    
    @auth("admin", "editor") {
        <button>Logout</button>
    }
    
    @guest {
        <button>Login</button>
    }
    
    @csrf
    @method("PUT")
    @old("email", "default@site.com")
    <input type="checkbox" @checked(active)>
    <option @selected(item.id == 1)>One</option>
    <input @disabled(true) @readonly(false)>
    
    @css("app.css")
    @js("app.js")
    @vite("main.ts")
    
    @json(my_dict)
    @dump(user)
    
    @let x = 10
    @fragment("inbox") {
        <ul id="inbox"></ul>
    }
"""

ext = EdenDirectivesExtension(Environment())
processed = ext.preprocess(source, "test.html")
print(processed)
