
from eden.templating.lexer import TemplateLexer
from eden.templating.parser import TemplateParser, DirectiveNode
from eden.templating.compiler import TemplateCompiler
import pytest

def test_reactive_directive_parsing():
    template = """
    @reactive(task) {
        <p>{{ task.name }}</p>
    }
    """
    lexer = TemplateLexer(template)
    tokens = lexer.tokenize()
    parser = TemplateParser(tokens)
    nodes = parser.parse()
    
    # Find 'reactive' directive node (ignoring leading/trailing whitespace)
    active_nodes = [n for n in nodes if isinstance(n, DirectiveNode)]
    assert len(active_nodes) == 1
    node = active_nodes[0]
    assert node.name == "reactive"
    assert node.expression == "(task)"
    assert node.body is not None
    assert len(node.body) > 0

def test_reactive_directive_compilation():
    template = """@reactive(task) { <span>{{ task.name }}</span> }"""
    
    lexer = TemplateLexer(template)
    tokens = lexer.tokenize()
    parser = TemplateParser(tokens)
    nodes = parser.parse()
    
    compiler = TemplateCompiler()
    compiled = compiler.compile(nodes)
    
    # Check for core components in compiled output
    assert "get_sync_channel(task)" in compiled
    assert 'hx-sync="{{ __ch }}"' in compiled
    assert 'hx-trigger="updated:{{ __ch }} from:body, created:{{ __ch }} from:body"' in compiled
    assert 'hx-get="{{ request.url }}"' in compiled
    assert 'hx-target="this"' in compiled
    assert 'hx-swap="outerHTML"' in compiled
    assert '{% block fragment_sync_' in compiled
    assert '<span>{{ task.name }}</span>' in compiled
