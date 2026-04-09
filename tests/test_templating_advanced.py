
import pytest
from unittest.mock import MagicMock
from eden.templating.lexer import TemplateLexer
from eden.templating.parser import TemplateParser, TemplateSyntaxError, DirectiveNode, TextNode
from eden.templating.compiler import TemplateCompiler
from eden.templating.templates import EdenTemplates
from starlette.requests import Request

def test_lexer_email_detection():
    """Ensure emails are NOT matched as directives."""
    lexer = TemplateLexer("Contact at hello@world.com or @admin")
    tokens = lexer.tokenize()
    
    # Check that hello@world.com is kept as text
    # hello matches TEXT, @ matches TEXT (because world.com follow-up makes it not a directive), world.com matches TEXT
    # Wait, my lexer handles @ directly.
    # Current behavior should be: "Contact at hello" (TEXT), "@" (TEXT), "world.com" (TEXT), " or " (TEXT), "admin" (DIRECTIVE)
    
    directives = [t for t in tokens if t.type.name == 'DIRECTIVE']
    assert len(directives) == 1
    assert directives[0].value == "admin"

def test_parser_unclosed_block():
    """Ensure unclosed blocks raise TemplateSyntaxError."""
    lexer = TemplateLexer("@if(True) { Hello")
    tokens = lexer.tokenize()
    parser = TemplateParser(tokens)
    
    with pytest.raises(TemplateSyntaxError) as excinfo:
        parser.parse()
    assert "Unclosed block for @if" in str(excinfo.value)

def test_compiler_props_dynamic():
    """Ensure @props handles dynamic values and alternate syntax."""
    compiler = TemplateCompiler()
    
    # List syntax
    res = compiler.handle_props("['title', 'count']")
    assert "{% set title = title if title is defined else None %}" in res
    assert "{% set count = count if count is defined else None %}" in res
    
    # Dict syntax with dynamic value
    res = compiler.handle_props("['title' => $default_title, 'count' => 0]")
    assert "{% set title = title if title is defined else default_title %}" in res
    assert "{% set count = count if count is defined else 0 %}" in res
    
    # Colon syntax
    res = compiler.handle_props("{'theme': 'dark'}")
    assert "{% set theme = theme if theme is defined else 'dark' %}" in res

def test_compiler_class_logic():
    """Ensure @class handles dynamic class logic."""
    compiler = TemplateCompiler()
    res = compiler.handle_class("['bg-red-500' => $error, 'p-4']")
    assert 'class="{{ (("bg-red-500" if error else "") + " " + "p-4").strip() }}"' in res

@pytest.mark.asyncio
async def test_templates_stacking():
    """Test @push and @stack helpers."""
    templates = EdenTemplates(directory="/tmp")
    scope = {"type": "http", "state": {}}
    request = Request(scope)
    request.state.eden_stacks = {}
    
    from eden.context import set_request
    set_request(request)
    
    # Push content
    templates._push_helper("scripts", '<script src="app.js"></script>')
    templates._push_helper("scripts", '<script src="extra.js"></script>')
    
    assert "scripts" in request.state.eden_stacks
    assert len(request.state.eden_stacks["scripts"]) == 2
    
    # Render stack - should return placeholder now for lazy replacement
    stack_content = templates._stack_helper("scripts")
    assert stack_content == "[[EDEN_STACK:scripts]]"

def test_templates_dependency_injection():
    """Test @inject helper."""
    templates = EdenTemplates(directory="/tmp")
    app = MagicMock()
    app.my_service = "ServiceInstance"
    # Ensure app.config and its children don't return mocks for everything
    app.config = MagicMock()
    app.config.unknown = None
    del app.unknown
    
    from eden.context import set_app
    set_app(app)
    
    res = templates._dependency_helper("my_service")
    assert res == "ServiceInstance"
    
    res = templates._dependency_helper("unknown")
    assert res is None

def test_conditional_grouping():
    """Test that if/else chains are grouped correctly."""
    source = """
    @if(True) {
        Yes
    } @else {
        No
    }
    """
    lexer = TemplateLexer(source)
    tokens = lexer.tokenize()
    parser = TemplateParser(tokens)
    nodes = parser.parse()
    # Filter out empty/whitespace nodes from surrounding source
    nodes = [n for n in nodes if not (isinstance(n, TextNode) and n.content.isspace())]
    
    # Should be one DirectiveNode(if) with orelse containing the else DirectiveNode
    assert len(nodes) == 1
    if_node = nodes[0]
    assert if_node.name == "if"
    assert len(if_node.orelse) > 0
    else_node = [n for n in if_node.orelse if isinstance(n, DirectiveNode) and n.name == "else"][0]
    assert else_node.name == "else"

def test_role_permission_directives():
    """Test role and permission directive generation."""
    from eden.template_directives import render_role, render_permission
    compiler = MagicMock(spec=TemplateCompiler)
    node = MagicMock()
    node.body = []
    
    # @role("admin")
    res = render_role(compiler, node, '"admin"')
    assert 'request.user.role == "admin"' in res
    
    # @role("admin, editor")
    res = render_role(compiler, node, '"admin", "editor"')
    assert "request.user.role in ('admin', 'editor')" in res
    
    # @permission("edit")
    res = render_permission(compiler, node, '"edit"')
    assert 'request.user.has_permission("edit")' in res
