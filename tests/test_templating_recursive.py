
import pytest
from eden.templating.lexer import TemplateLexer
from eden.templating.parser import TemplateParser, DirectiveNode, TextNode
from eden.templating.compiler import TemplateCompiler

def test_recursive_directive_parsing():
    """Ensure @recursive and @child are parsed correctly into a tree structure."""
    source = """
    @recursive($items as $item) {
        <li>{{ $item.name }}</li>
        @if($item.children) {
            <ul>
                @child($item.children)
            </ul>
        }
    }
    """
    lexer = TemplateLexer(source)
    tokens = lexer.tokenize()
    parser = TemplateParser(tokens)
    nodes = parser.parse()
    
    # Filter whitespace
    nodes = [n for n in nodes if not (isinstance(n, TextNode) and n.content.isspace())]
    
    assert len(nodes) == 1
    recursive_node = nodes[0]
    assert isinstance(recursive_node, DirectiveNode)
    assert recursive_node.name == "recursive"
    assert recursive_node.expression == "$items as $item" or recursive_node.expression == "($items as $item)"
    
    # Check body for child directive
    body = recursive_node.body
    body_filtered = [n for n in body if not (isinstance(n, TextNode) and n.content.isspace())]
    
    # body has: <li>{{ $item.name }}</li>, @if
    assert any(isinstance(n, DirectiveNode) and n.name == "if" for n in body_filtered)
    
    if_node = [n for n in body_filtered if isinstance(n, DirectiveNode) and n.name == "if"][0]
    if_body = if_node.body
    if_body_filtered = [n for n in if_body if not (isinstance(n, TextNode) and n.content.isspace())]
    
    # if_body has: <ul>, @child, </ul>
    # Wait, <ul> and </ul> are TextNodes if they don't have directives in them, but here they are separate.
    child_node = [n for n in if_body_filtered if isinstance(n, DirectiveNode) and n.name == "child"][0]
    assert child_node.name == "child"
    assert child_node.expression == "$item.children" or child_node.expression == "($item.children)"

def test_recursive_directive_compilation():
    """Ensure @recursive and @child compile to correct Jinja2 recursive loop syntax."""
    compiler = TemplateCompiler()
    
    # Create @recursive node
    recursive_node = DirectiveNode(
        name="recursive",
        expression="$items as $item",
        body=[
            TextNode(content="Name: {{ item.name }} "),
            DirectiveNode(
                name="child",
                expression="$item.children"
            )
        ]
    )
    
    res = compiler.visit(recursive_node)
    
    # Should compile to {% for item in items recursive %} ... {{ loop(item.children) }} ... {% endfor %}
    assert "{% for item in items recursive %}" in res
    assert "{{ loop(item.children) }}" in res
    assert "{% endfor %}" in res

def test_recursive_with_empty_compilation():
    """Ensure @recursive handles @empty/@else correctly via grouping."""
    compiler = TemplateCompiler()
    
    # Create @recursive node with orelse
    recursive_node = DirectiveNode(
        name="recursive",
        expression="$items as $item",
        body=[TextNode(content="{{ item.name }}")],
        orelse=[
            TextNode(content=" "),
            DirectiveNode(
                name="empty",
                body=[TextNode(content="No items found")]
            )
        ]
    )
    
    res = compiler.visit(recursive_node)
    
    assert "{% for item in items recursive %}" in res
    assert "{% else %}" in res
    assert "No items found" in res
    assert "{% endfor %}" in res

def test_recurse_alias_compilation():
    """Ensure @recurse is an alias for @child."""
    compiler = TemplateCompiler()
    
    node = DirectiveNode(name="recurse", expression="$children")
    res = compiler.visit(node)
    
    assert "{{ loop(children) }}" in res
