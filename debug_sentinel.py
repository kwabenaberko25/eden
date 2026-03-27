from __future__ import annotations
import uvicorn
from eden.app import Eden
from eden.requests import Request
from eden.templating.templates import EdenTemplates
from jinja2 import Environment, DictLoader
import os

# 1. Setup Mock Templates with Errors
templates_dict = {
    "undefined.eden": """
    @if (True) {
        <p>Hello, {{ missing_var }}</p>
    }
    """,
    "syntax.eden": """
    @if (True) {
        <p>This block is unclosed...
    """,
    "directive.eden": """
    @iff (True) {
        <p>Misspelled directive</p>
    }
    """
}

# 2. Configure Eden App
app = Eden(debug=True)
templates = EdenTemplates(loader=DictLoader(templates_dict))

@app.get("/undefined")
async def test_undefined(request: Request):
    return templates.TemplateResponse("undefined.eden", {"request": request})

@app.get("/syntax")
async def test_syntax(request: Request):
    return templates.TemplateResponse("syntax.eden", {"request": request})

@app.get("/directive")
async def test_directive(request: Request):
    return templates.TemplateResponse("directive.eden", {"request": request})

@app.get("/error")
async def test_generic_error(request: Request):
    # This should trigger render_enhanced_exception
    x = 1 / 0
    return {"result": x}

if __name__ == "__main__":
    print("🚀 Starting Debug Sentinel...")
    print("Testing coordinates and NameError fixes...")
    uvicorn.run(app, host="127.0.0.1", port=8000)
