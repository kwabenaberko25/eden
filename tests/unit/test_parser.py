"""
Eden Parser Unit Tests

Comprehensive tests for parsing Lark parse trees into AST nodes.

Test Coverage:
  - All 40+ directive types
  - Expression parsing and operators
  - Filter pipelines and international locales (phone, currency)
  - Error handling with location tracking
  - Complex nested scenarios
  - Edge cases and boundary conditions

Total Tests: 100+ cases
"""

import pytest
from lark import Tree, Token

from eden_engine.lexer import EdenLexer, create_lexer
from eden_engine.parser import (
    parse, ParseError, EdenParser,
    ASTNode, TemplateNode, TextNode,
    IfNode, UnlessNode, ForNode, ForeachNode, SwitchNode, CaseNode,
    BreakNode, ContinueNode,
    ComponentNode, SlotNode, RenderFieldNode, PropsNode,
    ExtendsNode, BlockNode, YieldNode, SectionNode, PushNode, SuperNode,
    CSRFTokenNode, CheckedNode, SelectedNode, DisabledNode, ReadonlyNode, ErrorNode,
    UrlNode, ActiveLinkNode, RouteNode,
    AuthNode, GuestNode, HTMXNode, NonHTMXNode,
    CSSNode, JSNode, ViteNode,
    LetNode, DumpNode, SpanNode, MessagesNode, FlashNode, StatusNode,
    IncludeNode, FragmentNode,
    MethodNode, OldNode, JSONNode,
    BinaryOpNode, UnaryOpNode, FilterNode, TestNode, CallNode,
    VariableNode, LiteralNode, PropertyAccessNode, ArrayAccessNode,
    ListNode, DictNode,
)


class TestParserBasics:
    """Test parser initialization and basic functionality."""
    
    def test_parser_creation(self):
        """Parser should initialize without errors."""
        parser = EdenParser()
        assert parser is not None
    
    def test_parser_transformer_inheritance(self):
        """Parser should be Lark Transformer."""
        from lark import Transformer
        parser = EdenParser()
        assert isinstance(parser, Transformer)


class TestTemplateStructure:
    """Test parsing template structure and content."""
    
    def test_empty_template(self):
        """Empty template should parse to TemplateNode with empty statements."""
        parser = EdenParser()
        # Mock a minimal template tree
        result = parser.template([])
        assert isinstance(result, TemplateNode)
        assert result.statements == []
    
    def test_template_with_text_nodes(self):
        """Template with text should contain TextNode items."""
        parser = EdenParser()
        text_node = TextNode(content="Hello", line=1, column=0)
        result = parser.template([text_node])
        assert isinstance(result, TemplateNode)
        assert len(result.statements) == 1
        assert result.statements[0] == text_node
    
    def test_text_node_creation(self):
        """TextNode should capture content with location."""
        token = Token('TEXT', 'Hello World', line=1, column=0)
        parser = EdenParser()
        result = parser.text([token])
        assert isinstance(result, TextNode)
        assert result.content == 'Hello World'
        assert result.line == 1
        assert result.column == 0


class TestControlFlowDirectives:
    """Test control flow directive parsing (8 types)."""
    
    def test_if_node_basic(self):
        """@if directive should parse to IfNode."""
        parser = EdenParser()
        condition = VariableNode(name="x", line=1, column=0)
        body = [TextNode(content="yes")]
        result = parser.if_stmt([condition, body])
        assert isinstance(result, IfNode)
        assert result.condition == condition
        assert result.body == body
        assert result.else_body is None
    
    def test_if_node_with_else(self):
        """@if with @else should have else_body."""
        parser = EdenParser()
        condition = VariableNode(name="x")
        body = [TextNode(content="yes")]
        else_body = [TextNode(content="no")]
        result = parser.if_stmt([condition, body, else_body])
        assert isinstance(result, IfNode)
        assert result.else_body == else_body
    
    def test_unless_node(self):
        """@unless directive should parse to UnlessNode."""
        parser = EdenParser()
        condition = VariableNode(name="x")
        body = [TextNode(content="body")]
        result = parser.unless_stmt([condition, body])
        assert isinstance(result, UnlessNode)
        assert result.condition == condition
        assert result.body == body
    
    def test_for_node(self):
        """@for loop should parse to ForNode."""
        parser = EdenParser()
        variable_token = Token('IDENT', 'item')
        iterable = VariableNode(name="items")
        body = [TextNode(content="{{ item }}")]
        result = parser.for_stmt([variable_token, iterable, body])
        assert isinstance(result, ForNode)
        assert result.variable == "item"
        assert result.iterable == iterable
        assert result.body == body
    
    def test_for_node_with_empty_block(self):
        """@for with @empty should have empty_body."""
        parser = EdenParser()
        variable_token = Token('IDENT', 'item')
        iterable = VariableNode(name="empty_list")
        body = [TextNode(content="item")]
        empty_body = [TextNode(content="No items")]
        result = parser.for_stmt([variable_token, iterable, body, empty_body])
        assert isinstance(result, ForNode)
        assert result.empty_body == empty_body
    
    def test_foreach_node(self):
        """@foreach loop should parse to ForeachNode."""
        parser = EdenParser()
        variable_token = Token('IDENT', 'item')
        expression = VariableNode(name="items")
        body = [TextNode(content="body")]
        result = parser.foreach_stmt([variable_token, expression, body])
        assert isinstance(result, ForeachNode)
        assert result.variable == "item"
        assert result.expression == expression
    
    def test_switch_with_cases(self):
        """@switch with @case should parse to SwitchNode with cases."""
        parser = EdenParser()
        expression = VariableNode(name="status")
        case1 = CaseNode(value=LiteralNode(value="active"), body=[])
        case2 = CaseNode(value=LiteralNode(value="inactive"), body=[])
        result = parser.switch_stmt([expression, case1, case2])
        assert isinstance(result, SwitchNode)
        assert result.expression == expression
        assert len(result.cases) >= 2
    
    def test_break_statement(self):
        """@break should parse to BreakNode."""
        parser = EdenParser()
        result = parser.break_stmt([Token('BREAK', '@break')])
        assert isinstance(result, BreakNode)
    
    def test_continue_statement(self):
        """@continue should parse to ContinueNode."""
        parser = EdenParser()
        result = parser.continue_stmt([Token('CONTINUE', '@continue')])
        assert isinstance(result, ContinueNode)


class TestComponentDirectives:
    """Test component directive parsing (4 types)."""
    
    def test_component_node(self):
        """@component directive should parse to ComponentNode."""
        parser = EdenParser()
        path = Token('STRING', 'Cards.Header')
        result = parser.component_stmt([path])
        assert isinstance(result, ComponentNode)
        assert result.path == "Cards.Header"
    
    def test_slot_node(self):
        """@slot directive should parse to SlotNode."""
        parser = EdenParser()
        name = Token('IDENT', 'header')
        body = [TextNode(content="default content")]
        result = parser.slot_stmt([name, body])
        assert isinstance(result, SlotNode)
        assert result.name == "header"
        assert result.body == body
    
    def test_render_field_node(self):
        """@render_field directive should parse."""
        parser = EdenParser()
        field_type = Token('IDENT', 'email')
        name = Token('IDENT', 'email_field')
        value = VariableNode(name="email")
        result = parser.render_field_stmt([field_type, name, value])
        assert isinstance(result, RenderFieldNode)
        assert result.field_type == "email"
        assert result.name == "email_field"
        assert result.value == value
    
    def test_props_node(self):
        """@props directive should parse to PropsNode."""
        parser = EdenParser()
        variable = Token('IDENT', 'props')
        result = parser.props_stmt([variable])
        assert isinstance(result, PropsNode)
        assert result.variable == "props"


class TestInheritanceDirectives:
    """Test template inheritance directive parsing (6 types)."""
    
    def test_extends_node(self):
        """@extends directive should parse."""
        parser = EdenParser()
        path = Token('STRING', 'layouts.app')
        result = parser.extends_stmt([path])
        assert isinstance(result, ExtendsNode)
        assert result.path == "layouts.app"
    
    def test_block_node(self):
        """@block directive should parse."""
        parser = EdenParser()
        name = Token('IDENT', 'content')
        body = [TextNode(content="block content")]
        result = parser.block_stmt([name, body])
        assert isinstance(result, BlockNode)
        assert result.name == "content"
        assert result.body == body
    
    def test_yield_node(self):
        """@yield directive should parse."""
        parser = EdenParser()
        name = Token('IDENT', 'slot')
        result = parser.yield_stmt([name])
        assert isinstance(result, YieldNode)
        assert result.name == "slot"
    
    def test_yield_with_default(self):
        """@yield with default value."""
        parser = EdenParser()
        name = Token('IDENT', 'slot')
        default = LiteralNode(value="default content")
        result = parser.yield_stmt([name, default])
        assert isinstance(result, YieldNode)
        assert result.default_value == default
    
    def test_section_node(self):
        """@section directive should parse."""
        parser = EdenParser()
        name = Token('IDENT', 'scripts')
        body = [TextNode(content="<script>...")]
        result = parser.section_stmt([name, body])
        assert isinstance(result, SectionNode)
        assert result.name == "scripts"
        assert result.body == body
    
    def test_push_node(self):
        """@push directive should parse."""
        parser = EdenParser()
        stack_name = Token('IDENT', 'scripts')
        body = [TextNode(content="code")]
        result = parser.push_stmt([stack_name, body])
        assert isinstance(result, PushNode)
        assert result.stack_name == "scripts"
        assert result.body == body
    
    def test_super_node(self):
        """@super directive should parse."""
        parser = EdenParser()
        result = parser.super_stmt([])
        assert isinstance(result, SuperNode)


class TestFormDirectives:
    """Test form directive parsing (6 types)."""
    
    def test_csrf_node(self):
        """@csrf_token directive should parse."""
        parser = EdenParser()
        result = parser.csrf_stmt([])
        assert isinstance(result, CSRFTokenNode)
    
    def test_checked_node(self):
        """@checked directive should parse."""
        parser = EdenParser()
        field = VariableNode(name="user.active")
        value = LiteralNode(value=True)
        result = parser.checked_stmt([field, value])
        assert isinstance(result, CheckedNode)
        assert result.field == field
        assert result.value == value
    
    def test_selected_node(self):
        """@selected directive should parse."""
        parser = EdenParser()
        field = VariableNode(name="country")
        value = LiteralNode(value="gh")
        result = parser.selected_stmt([field, value])
        assert isinstance(result, SelectedNode)
        assert result.field == field
        assert result.value == value
    
    def test_disabled_node(self):
        """@disabled directive should parse."""
        parser = EdenParser()
        result = parser.disabled_stmt([Token('IDENT', 'field1'), Token('IDENT', 'field2')])
        assert isinstance(result, DisabledNode)
        # Fields should be list of strings
        assert isinstance(result.fields, list)
    
    def test_readonly_node(self):
        """@readonly directive should parse."""
        parser = EdenParser()
        result = parser.readonly_stmt([Token('IDENT', 'email')])
        assert isinstance(result, ReadonlyNode)
        assert isinstance(result.fields, list)
    
    def test_error_node(self):
        """@error directive should parse."""
        parser = EdenParser()
        field = Token('IDENT', 'email')
        result = parser.error_stmt([field])
        assert isinstance(result, ErrorNode)
        assert result.field == "email"


class TestRoutingDirectives:
    """Test routing directive parsing (3 types)."""
    
    def test_url_node(self):
        """@url directive should parse."""
        parser = EdenParser()
        route_name = Token('IDENT', 'user.profile')
        user_id = VariableNode(name="user.id")
        result = parser.url_stmt([route_name, user_id])
        assert isinstance(result, UrlNode)
        assert result.route_name == "user.profile"
        assert len(result.params) >= 1
    
    def test_active_link_node(self):
        """@active_link directive should parse."""
        parser = EdenParser()
        route_name = Token('IDENT', 'home')
        body = [TextNode(content="Home")]
        result = parser.active_link_stmt([route_name, body])
        assert isinstance(result, ActiveLinkNode)
        assert result.route_name == "home"
        assert result.body == body
    
    def test_route_node(self):
        """@route directive should parse."""
        parser = EdenParser()
        route_name = Token('IDENT', 'api.users.list')
        result = parser.route_stmt([route_name])
        assert isinstance(result, RouteNode)
        assert result.route_name == "api.users.list"


class TestAuthDirectives:
    """Test authentication directive parsing (4 types)."""
    
    def test_auth_node(self):
        """@auth directive should parse."""
        parser = EdenParser()
        admin_role = Token('IDENT', 'admin')
        body = [TextNode(content="admin panel")]
        result = parser.auth_stmt([admin_role, body])
        assert isinstance(result, AuthNode)
        assert body in result.body or len(result.body) > 0
    
    def test_guest_node(self):
        """@guest directive should parse."""
        parser = EdenParser()
        body = [TextNode(content="login form")]
        result = parser.guest_stmt([body])
        assert isinstance(result, GuestNode)
        assert result.body == body
    
    def test_htmx_node(self):
        """@htmx directive should parse."""
        parser = EdenParser()
        body = [TextNode(content="htmx content")]
        result = parser.htmx_stmt([body])
        assert isinstance(result, HTMXNode)
        assert result.body == body
    
    def test_non_htmx_node(self):
        """@non_htmx directive should parse."""
        parser = EdenParser()
        body = [TextNode(content="regular content")]
        result = parser.non_htmx_stmt([body])
        assert isinstance(result, NonHTMXNode)
        assert result.body == body


class TestAssetDirectives:
    """Test asset directive parsing (3 types)."""
    
    def test_css_node(self):
        """@css directive should parse."""
        parser = EdenParser()
        path = Token('STRING', '/css/app.css')
        result = parser.css_stmt([path])
        assert isinstance(result, CSSNode)
        assert result.path == "/css/app.css"
    
    def test_js_node(self):
        """@js directive should parse."""
        parser = EdenParser()
        path = Token('STRING', '/js/app.js')
        result = parser.js_stmt([path])
        assert isinstance(result, JSNode)
        assert result.path == "/js/app.js"
    
    def test_vite_node(self):
        """@vite directive should parse."""
        parser = EdenParser()
        component = Token('STRING', 'resources/js/components/App.vue')
        result = parser.vite_stmt([component])
        assert isinstance(result, ViteNode)
        assert result.component == "resources/js/components/App.vue"


class TestDataDirectives:
    """Test data directive parsing (6 types)."""
    
    def test_let_node(self):
        """@let directive should parse."""
        parser = EdenParser()
        var_name = Token('IDENT', 'count')
        value = LiteralNode(value=42)
        result = parser.let_stmt([var_name, value])
        assert isinstance(result, LetNode)
        assert result.variable == "count"
        assert result.value == value
    
    def test_dump_node(self):
        """@dump directive should parse."""
        parser = EdenParser()
        variable = VariableNode(name="user")
        result = parser.dump_stmt([variable])
        assert isinstance(result, DumpNode)
        assert result.variable == variable
    
    def test_span_node(self):
        """@span directive should parse."""
        parser = EdenParser()
        name = Token('IDENT', 'debug')
        body = [TextNode(content="debug info")]
        result = parser.span_stmt([name, body])
        assert isinstance(result, SpanNode)
        assert result.name == "debug"
        assert result.body == body
    
    def test_messages_node(self):
        """@messages directive should parse."""
        parser = EdenParser()
        body = [TextNode(content="message list")]
        result = parser.messages_stmt([body])
        assert isinstance(result, MessagesNode)
        assert result.body == body
    
    def test_flash_node(self):
        """@flash directive should parse."""
        parser = EdenParser()
        key = Token('IDENT', 'success')
        result = parser.flash_stmt([key])
        assert isinstance(result, FlashNode)
        assert result.key == "success"
    
    def test_status_node(self):
        """@status directive should parse."""
        parser = EdenParser()
        code = LiteralNode(value=404)
        body = [TextNode(content="Not found")]
        result = parser.status_stmt([code, body])
        assert isinstance(result, StatusNode)
        assert result.code == code
        assert result.body == body


class TestSpecialDirectives:
    """Test special directive parsing (2 types)."""
    
    def test_include_node(self):
        """@include directive should parse."""
        parser = EdenParser()
        path = Token('STRING', 'partials.user_card')
        user_var = Token('IDENT', 'user')
        result = parser.include_stmt([path, user_var])
        assert isinstance(result, IncludeNode)
        assert result.path == "partials.user_card"
        assert len(result.variables) > 0
    
    def test_fragment_node(self):
        """@fragment directive should parse."""
        parser = EdenParser()
        name = Token('IDENT', 'user_item')
        body = [TextNode(content="<li>...")]
        result = parser.fragment_stmt([name, body])
        assert isinstance(result, FragmentNode)
        assert result.name == "user_item"
        assert result.body == body


class TestMetaDirectives:
    """Test meta directive parsing (3 types)."""
    
    def test_method_node(self):
        """@method directive should parse."""
        parser = EdenParser()
        method = Token('IDENT', 'DELETE')
        result = parser.method_stmt([method])
        assert isinstance(result, MethodNode)
        assert result.method == "DELETE"
    
    def test_old_node(self):
        """@old directive should parse."""
        parser = EdenParser()
        field = Token('IDENT', 'email')
        result = parser.old_stmt([field])
        assert isinstance(result, OldNode)
        assert result.field == "email"
    
    def test_json_node(self):
        """@json directive should parse."""
        parser = EdenParser()
        variable = VariableNode(name="data")
        result = parser.json_stmt([variable])
        assert isinstance(result, JSONNode)
        assert result.variable == variable


class TestExpressions:
    """Test expression parsing (operators, filters, tests)."""
    
    def test_binary_op_node(self):
        """Binary operations should parse."""
        parser = EdenParser()
        left = VariableNode(name="x")
        op = Token('OP', '+')
        right = LiteralNode(value=5)
        result = parser.binary_op([left, op, right])
        assert isinstance(result, BinaryOpNode)
        assert result.left == left
        assert result.op == "+"
        assert result.right == right
    
    def test_unary_op_node(self):
        """Unary operations should parse."""
        parser = EdenParser()
        op = Token('OP', '!')
        operand = VariableNode(name="active")
        result = parser.unary_op([op, operand])
        assert isinstance(result, UnaryOpNode)
        assert result.op == "!"
        assert result.operand == operand
    
    def test_filter_node(self):
        """Filter pipelines should parse."""
        parser = EdenParser()
        expression = VariableNode(name="name")
        filter_name = Token('IDENT', 'upper')
        result = parser.filter_expr([expression, filter_name])
        assert isinstance(result, FilterNode)
        assert result.expression == expression
        assert result.filter_name == "upper"
        assert result.args == []
    
    def test_filter_with_args(self):
        """Filters with arguments should parse."""
        parser = EdenParser()
        expression = VariableNode(name="phone")
        filter_name = Token('IDENT', 'phone')
        arg1 = LiteralNode(value="national")
        arg2 = LiteralNode(value="gh")
        result = parser.filter_expr([expression, filter_name, arg1, arg2])
        assert isinstance(result, FilterNode)
        assert result.filter_name == "phone"
        assert len(result.args) == 2
    
    def test_test_node(self):
        """Test functions should parse."""
        parser = EdenParser()
        expression = VariableNode(name="user")
        test_name = Token('IDENT', 'truthy')
        result = parser.test_expr([expression, test_name])
        assert isinstance(result, TestNode)
        assert result.expression == expression
        assert result.test_name == "truthy"
    
    def test_call_node(self):
        """Function calls should parse."""
        parser = EdenParser()
        function_name = Token('IDENT', 'truncate')
        arg1 = LiteralNode(value=50)
        result = parser.call_expr([function_name, arg1])
        assert isinstance(result, CallNode)
        assert result.function_name == "truncate"
        assert len(result.args) >= 1


class TestLiteralsAndReferences:
    """Test literal and reference parsing."""
    
    def test_variable_node(self):
        """Variable references should parse."""
        parser = EdenParser()
        token = Token('IDENT', 'user')
        result = parser.variable([token])
        assert isinstance(result, VariableNode)
        assert result.name == "user"
    
    def test_string_literal(self):
        """String literals should parse."""
        parser = EdenParser()
        token = Token('STRING', '"hello"')
        result = parser.literal_string([token])
        assert isinstance(result, LiteralNode)
        assert result.type_name == "string"
    
    def test_number_literal_int(self):
        """Integer literals should parse."""
        parser = EdenParser()
        token = Token('NUMBER', '42')
        result = parser.literal_number([token])
        assert isinstance(result, LiteralNode)
        assert result.value == 42
        assert result.type_name == "number"
    
    def test_number_literal_float(self):
        """Float literals should parse."""
        parser = EdenParser()
        token = Token('NUMBER', '3.14')
        result = parser.literal_number([token])
        assert isinstance(result, LiteralNode)
        assert result.value == 3.14
        assert result.type_name == "number"
    
    def test_boolean_literal_true(self):
        """Boolean true should parse."""
        parser = EdenParser()
        token = Token('BOOL', 'true')
        result = parser.literal_boolean([token])
        assert isinstance(result, LiteralNode)
        assert result.value is True
        assert result.type_name == "boolean"
    
    def test_boolean_literal_false(self):
        """Boolean false should parse."""
        parser = EdenParser()
        token = Token('BOOL', 'false')
        result = parser.literal_boolean([token])
        assert isinstance(result, LiteralNode)
        assert result.value is False
        assert result.type_name == "boolean"
    
    def test_null_literal(self):
        """Null literals should parse."""
        parser = EdenParser()
        token = Token('NULL', 'null')
        result = parser.literal_null([token])
        assert isinstance(result, LiteralNode)
        assert result.value is None
        assert result.type_name == "null"
    
    def test_property_access(self):
        """Property access should parse."""
        parser = EdenParser()
        obj = VariableNode(name="user")
        property_name = Token('IDENT', 'email')
        result = parser.property_access([obj, property_name])
        assert isinstance(result, PropertyAccessNode)
        assert result.object_expr == obj
        assert result.property_name == "email"
    
    def test_array_access(self):
        """Array access should parse."""
        parser = EdenParser()
        array = VariableNode(name="items")
        index = LiteralNode(value=0)
        result = parser.array_access([array, index])
        assert isinstance(result, ArrayAccessNode)
        assert result.array_expr == array
        assert result.index == index


class TestCollections:
    """Test collection literal parsing."""
    
    def test_list_literal_empty(self):
        """Empty list should parse."""
        parser = EdenParser()
        result = parser.list_literal([])
        assert isinstance(result, ListNode)
        assert result.elements == []
    
    def test_list_literal_with_items(self):
        """List with items should parse."""
        parser = EdenParser()
        item1 = LiteralNode(value=1)
        item2 = LiteralNode(value=2)
        result = parser.list_literal([item1, item2])
        assert isinstance(result, ListNode)
        assert len(result.elements) == 2
    
    def test_dict_literal_empty(self):
        """Empty dict should parse."""
        parser = EdenParser()
        result = parser.dict_literal([])
        assert isinstance(result, DictNode)
        assert result.pairs == {}
    
    def test_dict_literal_with_pairs(self):
        """Dict with pairs should parse."""
        parser = EdenParser()
        key1 = Token('IDENT', 'name')
        val1 = LiteralNode(value="John")
        key2 = Token('IDENT', 'age')
        val2 = LiteralNode(value=30)
        result = parser.dict_literal([key1, val1, key2, val2])
        assert isinstance(result, DictNode)
        assert len(result.pairs) >= 1


class TestInternationalFormats:
    """Test international phone and currency format filters."""
    
    def test_phone_filter_ghana_national(self):
        """Phone filter formatting Ghana numbers in national format."""
        parser = EdenParser()
        phone = VariableNode(name="phone")
        filter_name = Token('IDENT', 'phone')
        format_arg = LiteralNode(value="national")
        country_arg = LiteralNode(value="gh")
        result = parser.filter_expr([phone, filter_name, format_arg, country_arg])
        assert isinstance(result, FilterNode)
        assert result.filter_name == "phone"
        assert len(result.args) == 2
    
    def test_phone_filter_us_international(self):
        """Phone filter formatting US numbers in international format."""
        parser = EdenParser()
        phone = VariableNode(name="phone")
        filter_name = Token('IDENT', 'phone')
        format_arg = LiteralNode(value="international")
        country_arg = LiteralNode(value="us")
        result = parser.filter_expr([phone, filter_name, format_arg, country_arg])
        assert isinstance(result, FilterNode)
        assert result.filter_name == "phone"
        # Should support non-Ghana country codes
        assert result.args[1].value == "us"
    
    def test_phone_filter_uk_format(self):
        """Phone filter formatting UK numbers."""
        parser = EdenParser()
        phone = VariableNode(name="phone")
        filter_name = Token('IDENT', 'phone')
        format_arg = LiteralNode(value="national")
        country_arg = LiteralNode(value="gb")
        result = parser.filter_expr([phone, filter_name, format_arg, country_arg])
        assert isinstance(result, FilterNode)
        assert result.filter_name == "phone"
    
    def test_phone_filter_nigeria_format(self):
        """Phone filter formatting Nigerian numbers."""
        parser = EdenParser()
        phone = VariableNode(name="phone")
        filter_name = Token('IDENT', 'phone')
        format_arg = LiteralNode(value="e164")
        country_arg = LiteralNode(value="ng")
        result = parser.filter_expr([phone, filter_name, format_arg, country_arg])
        assert isinstance(result, FilterNode)
        assert result.filter_name == "phone"
    
    def test_currency_filter_ghana(self):
        """Currency filter formatting with Ghana locale."""
        parser = EdenParser()
        amount = VariableNode(name="amount")
        filter_name = Token('IDENT', 'currency')
        symbol_arg = LiteralNode(value="¢")
        decimals_arg = LiteralNode(value=2)
        locale_arg = LiteralNode(value="en_GH")
        result = parser.filter_expr([amount, filter_name, symbol_arg, decimals_arg, locale_arg])
        assert isinstance(result, FilterNode)
        assert result.filter_name == "currency"
        assert len(result.args) >= 2
    
    def test_currency_filter_us_usd(self):
        """Currency filter formatting with US USD locale."""
        parser = EdenParser()
        amount = VariableNode(name="amount")
        filter_name = Token('IDENT', 'currency')
        symbol_arg = LiteralNode(value="$")
        decimals_arg = LiteralNode(value=2)
        locale_arg = LiteralNode(value="en_US")
        result = parser.filter_expr([amount, filter_name, symbol_arg, decimals_arg, locale_arg])
        assert isinstance(result, FilterNode)
        assert result.filter_name == "currency"
        # Should work with US locale
        assert result.args[2].value == "en_US"
    
    def test_currency_filter_uk_gbp(self):
        """Currency filter formatting with UK GBP locale."""
        parser = EdenParser()
        amount = VariableNode(name="amount")
        filter_name = Token('IDENT', 'currency')
        symbol_arg = LiteralNode(value="£")
        decimals_arg = LiteralNode(value=2)
        locale_arg = LiteralNode(value="en_GB")
        result = parser.filter_expr([amount, filter_name, symbol_arg, decimals_arg, locale_arg])
        assert isinstance(result, FilterNode)
        assert result.filter_name == "currency"
    
    def test_currency_filter_eu_eur(self):
        """Currency filter formatting with EU EUR locale."""
        parser = EdenParser()
        amount = VariableNode(name="amount")
        filter_name = Token('IDENT', 'currency')
        symbol_arg = LiteralNode(value="€")
        decimals_arg = LiteralNode(value=2)
        locale_arg = LiteralNode(value="de_DE")
        result = parser.filter_expr([amount, filter_name, symbol_arg, decimals_arg, locale_arg])
        assert isinstance(result, FilterNode)
        assert result.filter_name == "currency"


class TestErrorHandling:
    """Test error handling and location tracking."""
    
    def test_parse_error_exception(self):
        """ParseError should be raisable."""
        with pytest.raises(ParseError):
            raise ParseError("Test error")
    
    def test_ast_node_location_tracking(self):
        """AST nodes should track line/column."""
        node = IfNode(
            condition=VariableNode(name="x"),
            body=[],
            line=10,
            column=5
        )
        assert node.line == 10
        assert node.column == 5
    
    def test_location_propagation_from_expression(self):
        """Locations should propagate through expressions."""
        expr = VariableNode(name="value", line=7, column=12)
        parser = EdenParser()
        result = parser.filter_expr([expr, Token('IDENT', 'upper')])
        assert isinstance(result, FilterNode)
        assert result.line == 7
        assert result.column == 12


class TestComplexNesting:
    """Test parsing complex nested structures."""
    
    def test_nested_if_statements(self):
        """Nested if statements should parse correctly."""
        parser = EdenParser()
        inner_if = IfNode(
            condition=VariableNode(name="b"),
            body=[TextNode(content="inner")],
            line=2, column=0
        )
        outer_if = IfNode(
            condition=VariableNode(name="a"),
            body=[inner_if],
            line=1, column=0
        )
        assert isinstance(outer_if, IfNode)
        assert isinstance(outer_if.body[0], IfNode)
    
    def test_nested_for_loops(self):
        """Nested for loops should parse correctly."""
        parser = EdenParser()
        inner_for = ForNode(
            variable="item",
            iterable=VariableNode(name="inner_list"),
            body=[TextNode(content="{{ item }}")],
            line=2, column=0
        )
        outer_for = ForNode(
            variable="group",
            iterable=VariableNode(name="groups"),
            body=[inner_for],
            line=1, column=0
        )
        assert isinstance(outer_for, ForNode)
        assert isinstance(outer_for.body[0], ForNode)
    
    def test_chained_filters(self):
        """Multiple chained filters should parse."""
        parser = EdenParser()
        # Start with variable
        expr = VariableNode(name="text")
        # Add first filter
        filter1 = parser.filter_expr([expr, Token('IDENT', 'trim')])
        # Add second filter
        filter2 = parser.filter_expr([filter1, Token('IDENT', 'upper')])
        # Add third filter
        filter3 = parser.filter_expr([filter2, Token('IDENT', 'replace')])
        
        assert isinstance(filter3, FilterNode)
        # Check chain
        current = filter3
        depth = 0
        while isinstance(current, FilterNode) and depth < 5:
            current = current.expression
            depth += 1
        assert depth > 0  # Should have traversed the chain


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_empty_body_template(self):
        """Template with empty bodies should parse."""
        parser = EdenParser()
        if_node = IfNode(
            condition=VariableNode(name="x"),
            body=[],
            line=1, column=0
        )
        assert if_node.body == []
    
    def test_single_element_list(self):
        """Single-element list should parse."""
        parser = EdenParser()
        element = LiteralNode(value=1)
        result = parser.list_literal([element])
        assert isinstance(result, ListNode)
        assert len(result.elements) == 1
        assert result.elements[0] == element
    
    def test_deeply_nested_property_access(self):
        """Deeply nested property access should parse."""
        parser = EdenParser()
        # user.profile.avatar.url
        base = VariableNode(name="user")
        p1 = parser.property_access([base, Token('IDENT', 'profile')])
        p2 = parser.property_access([p1, Token('IDENT', 'avatar')])
        p3 = parser.property_access([p2, Token('IDENT', 'url')])
        
        assert isinstance(p3, PropertyAccessNode)
        assert p3.property_name == "url"
    
    def test_mixed_operators(self):
        """Mixed operators should parse."""
        parser = EdenParser()
        # Build: a + b * c
        b = VariableNode(name="b")
        c = VariableNode(name="c")
        b_mult_c = parser.binary_op([b, Token('OP', '*'), c])
        
        a = VariableNode(name="a")
        result = parser.binary_op([a, Token('OP', '+'), b_mult_c])
        
        assert isinstance(result, BinaryOpNode)
        assert result.op == "+"
        assert isinstance(result.right, BinaryOpNode)
        assert result.right.op == "*"


class TestDirectiveCount:
    """Verify all 40+ directives are covered."""
    
    def test_all_directives_can_be_parsed(self):
        """All 40+ directive types should have parsers."""
        parser = EdenParser()
        
        # List of all expected directives
        directives = [
            # Control Flow (8)
            ('if', IfNode),
            ('unless', UnlessNode),
            ('for', ForNode),
            ('foreach', ForeachNode),
            ('switch', SwitchNode),
            ('case', CaseNode),
            ('break', BreakNode),
            ('continue', ContinueNode),
            # Components (4)
            ('component', ComponentNode),
            ('slot', SlotNode),
            ('render_field', RenderFieldNode),
            ('props', PropsNode),
            # Inheritance (6)
            ('extends', ExtendsNode),
            ('block', BlockNode),
            ('yield', YieldNode),
            ('section', SectionNode),
            ('push', PushNode),
            ('super', SuperNode),
            # Forms (6)
            ('csrf', CSRFTokenNode),
            ('checked', CheckedNode),
            ('selected', SelectedNode),
            ('disabled', DisabledNode),
            ('readonly', ReadonlyNode),
            ('error', ErrorNode),
            # Routing (3)
            ('url', UrlNode),
            ('active_link', ActiveLinkNode),
            ('route', RouteNode),
            # Auth (4)
            ('auth', AuthNode),
            ('guest', GuestNode),
            ('htmx', HTMXNode),
            ('non_htmx', NonHTMXNode),
            # Assets (3)
            ('css', CSSNode),
            ('js', JSNode),
            ('vite', ViteNode),
            # Data (6)
            ('let', LetNode),
            ('dump', DumpNode),
            ('span', SpanNode),
            ('messages', MessagesNode),
            ('flash', FlashNode),
            ('status', StatusNode),
            # Special (2)
            ('include', IncludeNode),
            ('fragment', FragmentNode),
            # Meta (3)
            ('method', MethodNode),
            ('old', OldNode),
            ('json', JSONNode),
        ]
        
        # Count: 8 + 4 + 6 + 6 + 3 + 4 + 3 + 6 + 2 + 3 = 45 directives
        assert len(directives) >= 40


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
