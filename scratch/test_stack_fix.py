
import pytest
from starlette.requests import Request
from eden.templating.templates import EdenTemplates, EdenTemplateResponse

def test_stack_placeholder_replacement_empty():
    # Setup mock request
    class MockState:
        def __init__(self):
            self.eden_stacks = {}
            self.eden_seen_pushes = set()
    
    class MockRequest:
        def __init__(self):
            self.state = MockState()
            self.scope = {"type": "http"}

    request = MockRequest()
    templates = EdenTemplates(directory=".")
    
    # Manually create a response with a placeholder
    # In a real app, @stack('styles') would produce this
    content = "<html><head>[[EDEN_STACK:styles]]</head><body>Content</body></html>"
    
    # We need a real template object for EdenTemplateResponse
    from jinja2 import Template
    template = Template(content)
    
    response = EdenTemplateResponse(
        template=template,
        context={"request": request},
    )
    
    # response.body is set during __init__ by rendering and then calling our render override
    rendered = response.body.decode()
    
    # Assert that the placeholder is GONE even if empty
    assert "[[EDEN_STACK:styles]]" not in rendered
    assert "<html><head></head><body>Content</body></html>" in rendered or "<html><head>\n</head><body>Content</body></html>" in rendered

def test_stack_placeholder_replacement_with_content():
    # Setup mock request
    class MockState:
        def __init__(self):
            self.eden_stacks = {"styles": ["<link rel='stylesheet'>"]}
            self.eden_seen_pushes = set()
    
    class MockRequest:
        def __init__(self):
            self.state = MockState()
            self.scope = {"type": "http"}

    request = MockRequest()
    
    # Manually create a response with a placeholder
    content = "<html><head>[[EDEN_STACK:styles]]</head><body>Content</body></html>"
    
    from jinja2 import Template
    template = Template(content)
    
    response = EdenTemplateResponse(
        template=template,
        context={"request": request},
    )
    
    rendered = response.body.decode()
    
    # Assert that the placeholder is replaced with content
    assert "[[EDEN_STACK:styles]]" not in rendered
    assert "<link rel='stylesheet'>" in rendered
