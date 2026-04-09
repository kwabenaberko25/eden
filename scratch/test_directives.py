import asyncio
from eden.templating import EdenTemplates
from eden.requests import Request
from starlette.datastructures import Headers

async def test_directives():
    print("Testing Template Directives (@stack, @push, @prepend)...")
    
    # Setup templates
    import os
    os.makedirs("scratch/templates", exist_ok=True)
    
    with open("scratch/templates/base.html", "w") as f:
        f.write("""
<!DOCTYPE html>
<html>
<head>
    @stack('styles')
</head>
<body>
    @yield('content')
    @stack('scripts')
</body>
</html>
""")

    with open("scratch/templates/page.html", "w") as f:
        f.write("""
@extends('base.html')

@section('content') {
    @push('styles') {
        <link rel="stylesheet" href="style.css">
    }

    @prepend('styles') {
        <link rel="stylesheet" href="reset.css">
    }

    <h1>Hello World</h1>

    @push('scripts') {
        <script src="app.js"></script>
    }

    @prepend('scripts') {
        <script src="jquery.js"></script>
    }
}
""")

    templates = EdenTemplates(directory="scratch/templates")
    
    # Mock request
    request = Request(scope={
        "type": "http",
        "headers": Headers({"host": "localhost"}).raw,
        "state": {}
    })
    
    from eden.context import context_manager
    
    async def run_render():
        html_response = templates.render(request, "page.html", {})
        return str(html_response.body.decode())

    html = await context_manager.run_in_context(run_render, request=request)
    print("\nRendered HTML:")
    print("-" * 20)
    print(html)
    print("-" * 20)
    
    # Verification
    # Styles should have reset.css THEN style.css
    assert "reset.css" in html
    assert "style.css" in html
    reset_pos = html.find("reset.css")
    style_pos = html.find("style.css")
    assert reset_pos < style_pos, "prepend('styles') should come before push('styles')"
    
    # Scripts should have jquery.js THEN app.js
    assert "jquery.js" in html
    assert "app.js" in html
    jquery_pos = html.find("jquery.js")
    app_pos = html.find("app.js")
    assert jquery_pos < app_pos, "prepend('scripts') should come before push('scripts')"
    
    assert "<h1>Hello World</h1>" in html
    
    print("\n[SUCCESS] Template directives (@stack, @push, @prepend) working correctly.")

if __name__ == "__main__":
    asyncio.run(test_directives())
