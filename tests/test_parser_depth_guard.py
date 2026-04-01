import pytest
from eden.templating.parser import TemplateParser, TemplateSyntaxError, MAX_PARSE_DEPTH
from eden.templating.lexer import Lexer

def test_parser_depth_guard_success():
    # A template that is deep, but within MAX_PARSE_DEPTH
    template_str = ""
    for _ in range(MAX_PARSE_DEPTH - 10):
        template_str += "@if(True) {"
    template_str += "Hello"
    for _ in range(MAX_PARSE_DEPTH - 10):
        template_str += "}"

    tokens = Lexer(template_str).tokenize()
    parser = TemplateParser(tokens)
    nodes = parser.parse()
    assert bool(nodes) is True


def test_parser_depth_guard_exceeded():
    # A template that exceeds MAX_PARSE_DEPTH
    template_str = ""
    for _ in range(MAX_PARSE_DEPTH + 10):
        template_str += "@if(True) {"
    template_str += "Hello"
    for _ in range(MAX_PARSE_DEPTH + 10):
        template_str += "}"

    tokens = Lexer(template_str).tokenize()
    parser = TemplateParser(tokens)
    with pytest.raises(TemplateSyntaxError) as exc_info:
        parser.parse()
    
    assert "Maximum template nesting depth exceeded" in str(exc_info.value)
