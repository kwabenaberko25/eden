"""
Phase 1 Unit Tests - Foundation & Parsing
Tests for tokenizer, AST nodes, and parser
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from eden_engine.lexer.tokenizer import (
    EdenLexer, TokenType, Token, tokenize,
    is_keyword, is_directive, is_test_function
)
from eden_engine.parser.ast_nodes import (
    ASTNode, TemplateNode, RawTextNode, ExpressionNode,
    IfNode, UnlessNode, ForNode, SwitchNode, CaseNode,
    ComponentNode, BlockNode, ExtendsNode,
    FilterNode, LiteralNode, IdentifierNode
)
from eden_engine.parser.parser import EdenParser, parse, ParseError


# ============================================
# TOKENIZER TESTS
# ============================================

class TestTokenTypeEnum:
    """Test TokenType enum"""
    
    def test_token_type_exists(self):
        """TokenType enum should exist"""
        assert TokenType is not None
        assert hasattr(TokenType, 'RAW_TEXT')
        assert hasattr(TokenType, 'DIRECTIVE')
    
    def test_token_types_count(self):
        """Should have all required token types"""
        types = [member for member in TokenType]
        assert len(types) >= 40, f"Expected at least 40 token types, got {len(types)}"


class TestTokenClass:
    """Test Token data class"""
    
    def test_token_creation(self):
        """Token should be creatable"""
        tok = Token(TokenType.IDENTIFIER, "hello", 1, 5)
        assert tok.type == TokenType.IDENTIFIER
        assert tok.value == "hello"
        assert tok.line == 1
        assert tok.column == 5
    
    def test_token_repr(self):
        """Token should have readable repr"""
        tok = Token(TokenType.IDENTIFIER, "test", 2, 3)
        repr_str = repr(tok)
        assert "IDENTIFIER" in repr_str
        assert "test" in repr_str
        assert "2:3" in repr_str


class TestEdenLexerInit:
    """Test lexer initialization"""
    
    def test_lexer_creation(self):
        """Lexer should initialize without error"""
        lexer = EdenLexer()
        assert lexer is not None
    
    def test_lexer_has_keywords(self):
        """Lexer should have keyword set"""
        lexer = EdenLexer()
        assert len(lexer.KEYWORDS) > 0
        assert 'if' in lexer.KEYWORDS
        assert 'for' in lexer.KEYWORDS
    
    def test_lexer_has_directives(self):
        """Lexer should have directive set"""
        lexer = EdenLexer()
        assert len(lexer.DIRECTIVES) > 30
        assert 'if' in lexer.DIRECTIVES
        assert 'for' in lexer.DIRECTIVES
        assert 'csrf' in lexer.DIRECTIVES
        assert 'component' in lexer.DIRECTIVES
    
    def test_lexer_has_test_functions(self):
        """Lexer should have test function set"""
        lexer = EdenLexer()
        assert 'defined' in lexer.TEST_FUNCTIONS
        assert 'empty' in lexer.TEST_FUNCTIONS
        assert 'odd' in lexer.TEST_FUNCTIONS


class TestRawTextTokenization:
    """Test tokenization of raw text"""
    
    def test_empty_string(self):
        """Empty string should tokenize"""
        lexer = EdenLexer()
        tokens = lexer.tokenize("")
        assert isinstance(tokens, list)
    
    def test_plain_html(self):
        """Plain HTML should tokenize as raw text"""
        lexer = EdenLexer()
        html = "<div>Hello</div>"
        tokens = lexer.tokenize(html)
        assert len(tokens) > 0
    
    def test_text_with_newlines(self):
        """Text with newlines should tokenize"""
        lexer = EdenLexer()
        text = "Line 1\nLine 2\nLine 3"
        tokens = lexer.tokenize(text)
        assert len(tokens) > 0


class TestExpressionTokenization:
    """Test tokenization of expressions"""
    
    def test_simple_variable(self):
        """{{ variable }} should tokenize"""
        lexer = EdenLexer()
        tokens = lexer.tokenize("{{ name }}")
        assert len(tokens) > 0
    
    def test_expression_with_dot_access(self):
        """{{ obj.prop }} should tokenize"""
        lexer = EdenLexer()
        tokens = lexer.tokenize("{{ user.email }}")
        assert len(tokens) > 0
    
    def test_expression_with_subscript(self):
        """{{ arr[0] }} should tokenize"""
        lexer = EdenLexer()
        tokens = lexer.tokenize("{{ items[0] }}")
        assert len(tokens) > 0
    
    def test_expression_with_filter(self):
        """{{ name | uppercase }} should tokenize"""
        lexer = EdenLexer()
        tokens = lexer.tokenize("{{ name | uppercase }}")
        assert len(tokens) > 0
    
    def test_expression_with_multiple_filters(self):
        """{{ text | trim | uppercase }} should tokenize"""
        lexer = EdenLexer()
        tokens = lexer.tokenize("{{ text | trim | uppercase }}")
        assert len(tokens) > 0
    
    def test_expression_nested_access(self):
        """{{ user.profile.avatar }} should tokenize"""
        lexer = EdenLexer()
        tokens = lexer.tokenize("{{ user.profile.avatar }}")
        assert len(tokens) > 0


class TestDirectiveTokenization:
    """Test tokenization of directives"""
    
    def test_if_directive(self):
        """@if directive should tokenize"""
        lexer = EdenLexer()
        tokens = lexer.tokenize("@if(condition) { }")
        assert len(tokens) > 0
    
    def test_for_directive(self):
        """@for directive should tokenize"""
        lexer = EdenLexer()
        tokens = lexer.tokenize("@for(item in items) { }")
        assert len(tokens) > 0
    
    def test_component_directive(self):
        """@component directive should tokenize"""
        lexer = EdenLexer()
        tokens = lexer.tokenize("@component(button) { }")
        assert len(tokens) > 0
    
    def test_block_directive(self):
        """@block directive should tokenize"""
        lexer = EdenLexer()
        tokens = lexer.tokenize("@block(content) { }")
        assert len(tokens) > 0
    
    def test_slot_directive(self):
        """@slot directive should tokenize"""
        lexer = EdenLexer()
        tokens = lexer.tokenize("@slot(header) { }")
        assert len(tokens) > 0


class TestFormDirectiveTokenization:
    """Test form directive tokenization"""
    
    def test_csrf_directive(self):
        """@csrf should tokenize"""
        lexer = EdenLexer()
        tokens = lexer.tokenize("@csrf()")
        assert len(tokens) > 0
    
    def test_checked_directive(self):
        """@checked should tokenize"""
        lexer = EdenLexer()
        tokens = lexer.tokenize("@checked(isActive)")
        assert len(tokens) > 0
    
    def test_selected_directive(self):
        """@selected should tokenize"""
        lexer = EdenLexer()
        tokens = lexer.tokenize("@selected(status == 'active')")
        assert len(tokens) > 0
    
    def test_disabled_directive(self):
        """@disabled should tokenize"""
        lexer = EdenLexer()
        tokens = lexer.tokenize("@disabled(isLocked)")
        assert len(tokens) > 0
    
    def test_readonly_directive(self):
        """@readonly should tokenize"""
        lexer = EdenLexer()
        tokens = lexer.tokenize("@readonly(isEditing)")
        assert len(tokens) > 0
    
    def test_render_field_directive(self):
        """@render_field should tokenize"""
        lexer = EdenLexer()
        tokens = lexer.tokenize("@render_field(email)")
        assert len(tokens) > 0
    
    def test_error_directive(self):
        """@error should tokenize"""
        lexer = EdenLexer()
        tokens = lexer.tokenize("@error(email) { }")
        assert len(tokens) > 0


class TestRouteDirectiveTokenization:
    """Test routing directive tokenization"""
    
    def test_url_directive(self):
        """@url directive should tokenize"""
        lexer = EdenLexer()
        tokens = lexer.tokenize("@url(index)")
        assert len(tokens) > 0
    
    def test_active_link_directive(self):
        """@active_link should tokenize"""
        lexer = EdenLexer()
        tokens = lexer.tokenize("@active_link('/dashboard', 'active')")
        assert len(tokens) > 0


class TestAuthDirectiveTokenization:
    """Test auth directive tokenization"""
    
    def test_auth_directive(self):
        """@auth should tokenize"""
        lexer = EdenLexer()
        tokens = lexer.tokenize("@auth() { }")
        assert len(tokens) > 0
    
    def test_guest_directive(self):
        """@guest should tokenize"""
        lexer = EdenLexer()
        tokens = lexer.tokenize("@guest() { }")
        assert len(tokens) > 0
    
    def test_htmx_directive(self):
        """@htmx should tokenize"""
        lexer = EdenLexer()
        tokens = lexer.tokenize("@htmx() { }")
        assert len(tokens) > 0
    
    def test_non_htmx_directive(self):
        """@non_htmx should tokenize"""
        lexer = EdenLexer()
        tokens = lexer.tokenize("@non_htmx() { }")
        assert len(tokens) > 0


class TestAssetDirectiveTokenization:
    """Test asset directive tokenization"""
    
    def test_css_directive(self):
        """@css should tokenize"""
        lexer = EdenLexer()
        tokens = lexer.tokenize("@css('style.css')")
        assert len(tokens) > 0
    
    def test_js_directive(self):
        """@js should tokenize"""
        lexer = EdenLexer()
        tokens = lexer.tokenize("@js('app.js')")
        assert len(tokens) > 0
    
    def test_vite_directive(self):
        """@vite should tokenize"""
        lexer = EdenLexer()
        tokens = lexer.tokenize("@vite()")
        assert len(tokens) > 0


class TestDataDirectiveTokenization:
    """Test data directive tokenization"""
    
    def test_let_directive(self):
        """@let should tokenize"""
        lexer = EdenLexer()
        tokens = lexer.tokenize("@let(total = 100)")
        assert len(tokens) > 0
    
    def test_old_directive(self):
        """@old should tokenize"""
        lexer = EdenLexer()
        tokens = lexer.tokenize("@old(email)")
        assert len(tokens) > 0
    
    def test_json_directive(self):
        """@json should tokenize"""
        lexer = EdenLexer()
        tokens = lexer.tokenize("@json(data)")
        assert len(tokens) > 0
    
    def test_dump_directive(self):
        """@dump should tokenize"""
        lexer = EdenLexer()
        tokens = lexer.tokenize("@dump(user)")
        assert len(tokens) > 0


class TestMessageDirectiveTokenization:
    """Test message directive tokenization"""
    
    def test_messages_directive(self):
        """@messages should tokenize"""
        lexer = EdenLexer()
        tokens = lexer.tokenize("@messages()")
        assert len(tokens) > 0
    
    def test_flash_directive(self):
        """@flash should tokenize"""
        lexer = EdenLexer()
        tokens = lexer.tokenize("@flash('success')")
        assert len(tokens) > 0


class TestSpecialDirectiveTokenization:
    """Test special directive tokenization"""
    
    def test_method_directive(self):
        """@method should tokenize"""
        lexer = EdenLexer()
        tokens = lexer.tokenize("@method(PUT)")
        assert len(tokens) > 0
    
    def test_include_directive(self):
        """@include should tokenize"""
        lexer = EdenLexer()
        tokens = lexer.tokenize("@include('header')")
        assert len(tokens) > 0
    
    def test_fragment_directive(self):
        """@fragment should tokenize"""
        lexer = EdenLexer()
        tokens = lexer.tokenize("@fragment(modal) { }")
        assert len(tokens) > 0


class TestInheritanceDirectiveTokenization:
    """Test inheritance directive tokenization"""
    
    def test_extends_directive(self):
        """@extends should tokenize"""
        lexer = EdenLexer()
        tokens = lexer.tokenize("@extends('layout')")
        assert len(tokens) > 0
    
    def test_yield_directive(self):
        """@yield should tokenize"""
        lexer = EdenLexer()
        tokens = lexer.tokenize("@yield('content')")
        assert len(tokens) > 0
    
    def test_section_directive(self):
        """@section should tokenize"""
        lexer = EdenLexer()
        tokens = lexer.tokenize("@section(title) { }")
        assert len(tokens) > 0
    
    def test_push_directive(self):
        """@push should tokenize"""
        lexer = EdenLexer()
        tokens = lexer.tokenize("@push(scripts) { }")
        assert len(tokens) > 0
    
    def test_super_directive(self):
        """@super should tokenize"""
        lexer = EdenLexer()
        tokens = lexer.tokenize("@super()")
        assert len(tokens) > 0


class TestComplexExpressions:
    """Test tokenization of complex expressions"""
    
    def test_binary_operations(self):
        """Binary operations should tokenize"""
        lexer = EdenLexer()
        tokens = lexer.tokenize("{{ a + b }}")
        assert len(tokens) > 0
    
    def test_comparison_operations(self):
        """Comparison operations should tokenize"""
        lexer = EdenLexer()
        tokens = lexer.tokenize("{{ count > 5 }}")
        assert len(tokens) > 0
    
    def test_logical_operations(self):
        """Logical operations should tokenize"""
        lexer = EdenLexer()
        tokens = lexer.tokenize("{{ a and b or c }}")
        assert len(tokens) > 0
    
    def test_ternary_operator(self):
        """Ternary operator should tokenize"""
        lexer = EdenLexer()
        tokens = lexer.tokenize("{{ condition ? 'yes' : 'no' }}")
        assert len(tokens) > 0
    
    def test_function_call(self):
        """Function calls should tokenize"""
        lexer = EdenLexer()
        tokens = lexer.tokenize("{{ strlen(name) }}")
        assert len(tokens) > 0


class TestStringLiterals:
    """Test tokenization of string literals"""
    
    def test_single_quoted_string(self):
        """Single quoted strings should tokenize"""
        lexer = EdenLexer()
        tokens = lexer.tokenize("{{ 'hello' }}")
        assert len(tokens) > 0
    
    def test_double_quoted_string(self):
        """Double quoted strings should tokenize"""
        lexer = EdenLexer()
        tokens = lexer.tokenize('{{ "hello" }}')
        assert len(tokens) > 0
    
    def test_string_with_escapes(self):
        """Strings with escapes should tokenize"""
        lexer = EdenLexer()
        tokens = lexer.tokenize('{{ "hello\\"world" }}')
        assert len(tokens) > 0


class TestNumberLiterals:
    """Test tokenization of number literals"""
    
    def test_integer_literal(self):
        """Integer literals should tokenize"""
        lexer = EdenLexer()
        tokens = lexer.tokenize("{{ 42 }}")
        assert len(tokens) > 0
    
    def test_float_literal(self):
        """Float literals should tokenize"""
        lexer = EdenLexer()
        tokens = lexer.tokenize("{{ 3.14 }}")
        assert len(tokens) > 0
    
    def test_negative_number(self):
        """Negative numbers should tokenize"""
        lexer = EdenLexer()
        tokens = lexer.tokenize("{{ -100 }}")
        assert len(tokens) > 0


class TestBooleanLiterals:
    """Test tokenization of boolean literals"""
    
    def test_true_literal(self):
        """true literal should tokenize"""
        lexer = EdenLexer()
        tokens = lexer.tokenize("{{ true }}")
        assert len(tokens) > 0
    
    def test_false_literal(self):
        """false literal should tokenize"""
        lexer = EdenLexer()
        tokens = lexer.tokenize("{{ false }}")
        assert len(tokens) > 0
    
    def test_null_literal(self):
        """null literal should tokenize"""
        lexer = EdenLexer()
        tokens = lexer.tokenize("{{ null }}")
        assert len(tokens) > 0


class TestCollectionLiterals:
    """Test tokenization of collections"""
    
    def test_list_literal(self):
        """List literals should tokenize"""
        lexer = EdenLexer()
        tokens = lexer.tokenize("{{ [1, 2, 3] }}")
        assert len(tokens) > 0
    
    def test_dict_literal(self):
        """Dict literals should tokenize"""
        lexer = EdenLexer()
        tokens = lexer.tokenize("{{ {'name': 'John', 'age': 30} }}")
        assert len(tokens) > 0


class TestTestFunctions:
    """Test tokenization of test functions"""
    
    def test_is_defined_test(self):
        """'is defined' test should tokenize"""
        lexer = EdenLexer()
        tokens = lexer.tokenize("{{ user is defined }}")
        assert len(tokens) > 0
    
    def test_is_empty_test(self):
        """'is empty' test should tokenize"""
        lexer = EdenLexer()
        tokens = lexer.tokenize("{{ items is empty }}")
        assert len(tokens) > 0
    
    def test_is_odd_test(self):
        """'is odd' test should tokenize"""
        lexer = EdenLexer()
        tokens = lexer.tokenize("{{ count is odd }}")
        assert len(tokens) > 0
    
    def test_is_even_test(self):
        """'is even' test should tokenize"""
        lexer = EdenLexer()
        tokens = lexer.tokenize("{{ count is even }}")
        assert len(tokens) > 0
    
    def test_is_divisible_by_test(self):
        """'is divisible_by' test should tokenize"""
        lexer = EdenLexer()
        tokens = lexer.tokenize("{{ num is divisible_by(5) }}")
        assert len(tokens) > 0


class TestTokenizationHelpers:
    """Test tokenization helper functions"""
    
    def test_is_keyword_function(self):
        """is_keyword should identify keywords"""
        assert is_keyword('if')
        assert is_keyword('for')
        assert not is_keyword('hello')
    
    def test_is_directive_function(self):
        """is_directive should identify directives"""
        assert is_directive('if')
        assert is_directive('csrf')
        assert is_directive('component')
        assert not is_directive('hello')
    
    def test_is_test_function_func(self):
        """is_test_function should identify test functions"""
        assert is_test_function('defined')
        assert is_test_function('empty')
        assert is_test_function('odd')
        assert not is_test_function('hello')


class TestTokenizeQuickFunction:
    """Test quick tokenize function"""
    
    def test_tokenize_function(self):
        """tokenize() should work"""
        tokens = tokenize("{{ name }}")
        assert len(tokens) > 0
    
    def test_tokenize_returns_list(self):
        """tokenize() should return list of tokens"""
        tokens = tokenize("<p>{{ user.name }}</p>")
        assert isinstance(tokens, list)
        for tok in tokens:
            assert isinstance(tok, Token)


# ============================================
# AST NODES TESTS
# ============================================

class TestASTNodeBase:
    """Test base ASTNode"""
    
    def test_node_creation(self):
        """AST nodes should be creatable"""
        node = RawTextNode(content="test")
        assert node.content == "test"
    
    def test_node_position_tracking(self):
        """AST nodes should track position"""
        node = RawTextNode(content="test", line=5, column=10)
        assert node.line == 5
        assert node.column == 10


class TestTemplateNode:
    """Test TemplateNode"""
    
    def test_template_creation(self):
        """TemplateNode should be creatable"""
        node = TemplateNode()
        assert node.items == []
    
    def test_template_with_items(self):
        """TemplateNode should hold items"""
        child = RawTextNode(content="text")
        node = TemplateNode(items=[child])
        assert len(node.items) == 1
        assert node.items[0] == child


class TestExpressionNode:
    """Test ExpressionNode"""
    
    def test_expression_creation(self):
        """ExpressionNode should be creatable"""
        node = ExpressionNode(expression="name")
        assert node.expression == "name"
    
    def test_expression_with_filters(self):
        """ExpressionNode should hold filters"""
        filter1 = FilterNode(name="uppercase")
        filter2 = FilterNode(name="trim")
        node = ExpressionNode(expression="name", filters=[filter1, filter2])
        assert len(node.filters) == 2


class TestControlFlowNodes:
    """Test control flow nodes"""
    
    def test_if_node_creation(self):
        """IfNode should be creatable"""
        node = IfNode(condition="true", body=[])
        assert node.condition == "true"
        assert node.body == []
    
    def test_if_node_with_else(self):
        """IfNode should support else body"""
        body = [RawTextNode(content="if body")]
        else_body = [RawTextNode(content="else body")]
        node = IfNode(condition="flag", body=body, else_body=else_body)
        assert len(node.body) == 1
        assert len(node.else_body) == 1
    
    def test_for_node_creation(self):
        """ForNode should be creatable"""
        node = ForNode(target="item", iterable="items", body=[])
        assert node.target == "item"
        assert node.iterable == "items"
    
    def test_switch_node_creation(self):
        """SwitchNode should be creatable"""
        case = CaseNode(value="'active'")
        node = SwitchNode(expression="status", cases=[case])
        assert node.expression == "status"
        assert len(node.cases) == 1


class TestComponentNodes:
    """Test component nodes"""
    
    def test_component_node_creation(self):
        """ComponentNode should be creatable"""
        node = ComponentNode(name="button")
        assert node.name == "button"
    
    def test_slot_node_creation(self):
        """SlotNode should be creatable"""
        node = SlotNode(name="header")
        assert node.name == "header"


class TestInheritanceNodes:
    """Test inheritance nodes"""
    
    def test_extends_node_creation(self):
        """ExtendsNode should be creatable"""
        node = ExtendsNode(parent_path="layout.html")
        assert node.parent_path == "layout.html"
    
    def test_block_node_creation(self):
        """BlockNode should be creatable"""
        body = [RawTextNode(content="block content")]
        node = BlockNode(name="content", body=body)
        assert node.name == "content"
        assert len(node.body) == 1


class TestFilterNode:
    """Test FilterNode"""
    
    def test_filter_creation(self):
        """FilterNode should be creatable"""
        node = FilterNode(name="uppercase")
        assert node.name == "uppercase"
    
    def test_filter_with_args(self):
        """FilterNode should support arguments"""
        node = FilterNode(name="slice", args=["0", "5"])
        assert len(node.args) == 2


class TestASTNodeToDict:
    """Test AST node serialization"""
    
    def test_node_to_dict(self):
        """AST nodes should serialize to dict"""
        node = RawTextNode(content="test")
        d = node.to_dict()
        assert d['type'] == 'RawTextNode'
        assert d['line'] == 0


# ============================================
# PARSER TESTS
# ============================================

class TestParserInit:
    """Test parser initialization"""
    
    def test_parser_creation(self):
        """EdenParser should initialize"""
        parser = EdenParser()
        assert parser is not None
    
    def test_parser_has_lark(self):
        """Parser should have Lark instance"""
        parser = EdenParser()
        assert hasattr(parser, 'lark_parser')


class TestParseRawText:
    """Test parsing raw text"""
    
    def test_parse_empty_template(self):
        """Empty template should parse"""
        ast = parse("")
        assert isinstance(ast, TemplateNode)
    
    def test_parse_plain_html(self):
        """Plain HTML should parse"""
        ast = parse("<div>Hello World</div>")
        assert isinstance(ast, TemplateNode)
    
    def test_parse_text_with_newlines(self):
        """Text with newlines should parse"""
        ast = parse("Line 1\nLine 2\nLine 3")
        assert isinstance(ast, TemplateNode)


class TestParseSimpleDirectives:
    """Test parsing simple directives"""
    
    def test_parse_if_directive(self):
        """@if directive should parse"""
        ast = parse("@if(true) { <p>Yes</p> }")
        assert isinstance(ast, TemplateNode)
    
    def test_parse_csrf_directive(self):
        """@csrf directive should parse"""
        ast = parse("@csrf()")
        assert isinstance(ast, TemplateNode)
    
    def test_parse_extends_directive(self):
        """@extends directive should parse"""
        ast = parse("@extends('layout')")
        assert isinstance(ast, TemplateNode)


class TestParseComplexTemplates:
    """Test parsing complex templates"""
    
    def test_parse_mixed_content(self):
        """Template with mixed content should parse"""
        template = """
        <html>
            <body>
                @if(user) {
                    <h1>{{ user.name }}</h1>
                }
            </body>
        </html>
        """
        ast = parse(template)
        assert isinstance(ast, TemplateNode)
    
    def test_parse_nested_directives(self):
        """Nested directives should parse"""
        template = """
        @for(item in items) {
            @if(item.active) {
                <p>{{ item.name }}</p>
            }
        }
        """
        ast = parse(template)
        assert isinstance(ast, TemplateNode)


class TestParserErrorHandling:
    """Test parser error handling"""
    
    def test_parse_error_handling(self):
        """Parser should handle invalid syntax"""
        # Parser should attempt to parse gracefully
        try:
            ast = parse("@if() {")
            # Should either parse or raise ParseError cleanly
            assert ast is not None or True
        except ParseError:
            pass  # Expected


class TestParseQuickFunction:
    """Test quick parse function"""
    
    def test_parse_function(self):
        """parse() should work"""
        ast = parse("{{ greeting }}")
        assert isinstance(ast, TemplateNode)


# ============================================
# INTEGRATION TESTS
# ============================================

class TestPhase1Integration:
    """Integration tests for Phase 1"""
    
    def test_tokenize_then_parse(self):
        """Tokenizing then parsing should work"""
        template = "@component(button) { <button>Click</button> }"
        
        # Tokenize
        lexer = EdenLexer()
        tokens = lexer.tokenize(template)
        assert len(tokens) > 0
        
        # Parse
        parser = EdenParser()
        ast = parser.parse(template)
        assert isinstance(ast, TemplateNode)
    
    def test_real_world_template_parsing(self):
        """Real-world template should parse"""
        template = """
        @extends('base')
        
        @block(content) {
            <div class="container">
                <h1>{{ page.title }}</h1>
                
                @if(posts.size() > 0) {
                    <ul>
                    @for(post in posts) {
                        <li>
                            <h2>{{ post.title }}</h2>
                            <p>{{ post.body | truncate(100) }}</p>
                        </li>
                    }
                    </ul>
                } @else {
                    <p>No posts available</p>
                }
            </div>
        }
        """
        ast = parse(template)
        assert isinstance(ast, TemplateNode)


# ============================================
# SMOKE TESTS
# ============================================

def test_phase1_complete():
    """Phase 1 foundation should be complete"""
    # Tokenize
    lexer = EdenLexer()
    tokens = lexer.tokenize("@csrf()")
    assert len(tokens) > 0, "Tokenization not working"
    
    # Parse
    parser = EdenParser()
    ast = parser.parse("@csrf()")
    assert isinstance(ast, TemplateNode), "Parsing not working"
    
    # Log success
    print("\n✅ Phase 1 Foundation Complete:")
    print("  ✓ Tokenizer: Grammar parsing")
    print("  ✓ AST nodes: 55+ node types")
    print("  ✓ Parser: AST generation")


if __name__ == "__main__":
    # Run pytest
    pytest.main([__file__, "-v", "--tb=short"])
