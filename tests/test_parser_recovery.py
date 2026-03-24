"""
Tests for TemplateParser error recovery (Issue #18).

Verifies:
1. Unclosed blocks raise TemplateSyntaxError with helpful message
2. Stalled parser content is preserved (not silently dropped)
3. Properly closed blocks still work
4. Nested blocks parse correctly
5. Mismatched braces produce clear errors
"""

import pytest
from eden.templating.lexer import TemplateLexer
from eden.templating.parser import TemplateParser, TemplateSyntaxError, DirectiveNode, TextNode


def parse(template_str: str):
    """Helper: lex + parse a template string."""
    lexer = TemplateLexer(template_str)
    tokens = lexer.tokenize()
    parser = TemplateParser(tokens)
    return parser.parse()


class TestUnclosedBlocks:
    """Test that unclosed blocks produce clear error messages."""
    
    def test_unclosed_if_raises_error(self):
        """An @if without a closing } should raise TemplateSyntaxError."""
        with pytest.raises(TemplateSyntaxError, match="Unclosed block for @if"):
            parse("@if(true) { hello")
    
    def test_unclosed_for_raises_error(self):
        """An @for without a closing } should raise TemplateSyntaxError."""
        with pytest.raises(TemplateSyntaxError, match="Unclosed block for @for"):
            parse("@for(item in items) { <p>{{ item }}</p>")
    
    def test_error_message_includes_brace_hint(self):
        """Error message should mention mismatched braces."""
        with pytest.raises(TemplateSyntaxError, match="mismatched braces"):
            parse("@if(x) { hello")


class TestBlockRecovery:
    """Test that properly formed blocks still parse correctly."""
    
    def test_simple_if_block(self):
        """A properly closed @if block should parse without errors."""
        nodes = parse("@if(true) { hello }")
        assert len(nodes) > 0
        # Find the directive node
        directives = [n for n in nodes if isinstance(n, DirectiveNode)]
        assert len(directives) == 1
        assert directives[0].name == "if"
    
    def test_nested_if_blocks(self):
        """Nested @if blocks should parse correctly."""
        nodes = parse("@if(a) { @if(b) { inner } outer }")
        directives = [n for n in nodes if isinstance(n, DirectiveNode)]
        assert len(directives) >= 1
        outer_if = directives[0]
        assert outer_if.name == "if"
        assert outer_if.body is not None
        
        # The inner @if should be inside the body
        inner_directives = [n for n in outer_if.body if isinstance(n, DirectiveNode)]
        assert len(inner_directives) >= 1
        assert inner_directives[0].name == "if"
    
    def test_if_else_block(self):
        """@if/@else blocks should parse correctly."""
        nodes = parse("@if(x) { yes } @else { no }")
        directives = [n for n in nodes if isinstance(n, DirectiveNode)]
        assert any(d.name == "if" for d in directives)
    
    def test_for_block(self):
        """A properly closed @for block should parse."""
        nodes = parse("@for(item in items) { <li>item</li> }")
        directives = [n for n in nodes if isinstance(n, DirectiveNode)]
        assert any(d.name == "for" for d in directives)


class TestContentPreservation:
    """Test that parser stall doesn't silently drop content."""
    
    def test_text_preserved_in_block(self):
        """Text content inside blocks should be preserved."""
        nodes = parse("@if(true) { Hello World }")
        directives = [n for n in nodes if isinstance(n, DirectiveNode)]
        assert len(directives) == 1
        body = directives[0].body
        assert body is not None
        # The body should contain text content
        text_content = "".join(
            n.content for n in body if isinstance(n, TextNode)
        )
        assert "Hello World" in text_content
    
    def test_multiple_elements_in_block(self):
        """Multiple elements inside a block should all be preserved."""
        template = "@if(show) { <h1>Title</h1><p>Body</p> }"
        nodes = parse(template)
        directives = [n for n in nodes if isinstance(n, DirectiveNode)]
        assert len(directives) == 1
        body = directives[0].body
        text_content = "".join(
            n.content for n in body if isinstance(n, TextNode)
        )
        assert "Title" in text_content
        assert "Body" in text_content


class TestStandaloneDirectives:
    """Test that standalone directives (break, continue) parse cleanly."""
    
    def test_break_directive(self):
        """@break should parse without needing a block."""
        nodes = parse("@for(i in items) { @break }")
        directives = [n for n in nodes if isinstance(n, DirectiveNode)]
        assert directives[0].name == "for"
