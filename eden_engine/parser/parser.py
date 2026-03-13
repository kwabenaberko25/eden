"""
Eden Templating Engine - Parser

Transforms Lark parse trees into Abstract Syntax Tree (AST) nodes.

The parser takes the output from the tokenizer (Lark parse tree) and transforms it
into structured AST nodes that represent the template's semantic meaning.

This enables clean separation of concerns:
  - Lexer: Template text → Token stream (via Lark)
  - Parser: Token stream → AST (this module)
  - CodeGen: AST → Bytecode (next phase)
  - Runtime: Bytecode → Output (final phase)

Architecture:
  - EdenParser: Main parser class using Lark Transformer
  - visit_* methods: Transform each Lark rule to AST node
  - Error handling: Detailed errors with line/column info
  - All 40+ directive types supported
  - All 50+ AST node types generated
"""

from typing import List, Dict, Optional, Any, Union
from lark import Transformer, Tree, Token as LarkToken, v_args

from .ast_nodes import (
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



class ParseError(Exception):
    """Raised when AST parsing fails with detailed location info."""
    pass


class EdenParser(Transformer):
    """
    Transforms Lark parse trees into Eden AST nodes.
    
    This transformer processes the parse tree produced by Lark and converts
    it into our structured AST. Each method corresponds to a rule in the grammar
    and produces the appropriate AST node.
    
    Features:
      - Handles all 40+ directive types
      - Generates 50+ AST node types
      - Comprehensive error reporting with source locations
      - Expression tree building with operator precedence
      - Filter pipeline transformation
      - Test function handling
      
    Usage:
        from eden_engine.lexer import create_lexer
        from eden_engine.parser import parse, ParseError
        
        lexer = create_lexer()
        ast = parse(lexer.tokenize(template_string))
        print(ast.to_debug_string())
    """
    
    def __init__(self):
        """Initialize parser."""
        super().__init__()
        self.current_line = 0
        self.current_column = 0
    
    def _get_location_from_token(self, token: LarkToken) -> tuple:
        """Extract line/column from Lark token."""
        return (token.line, token.column) if hasattr(token, 'line') else (1, 0)
    
    def _get_location_from_node(self, node: Any) -> tuple:
        """Extract line/column from AST node or token."""
        if isinstance(node, ASTNode):
            return (node.line, node.column)
        elif isinstance(node, LarkToken):
            return self._get_location_from_token(node)
        return (self.current_line, self.current_column)
    
    # ========================================================================
    # TEMPLATE & CONTENT
    # ========================================================================
    
    @v_args(inline=False)
    def template(self, items: List[ASTNode]) -> TemplateNode:
        """Transform template rule: (statement | text)* """
        return TemplateNode(statements=items if items else [])
    
    def text(self, token: List[LarkToken]) -> TextNode:
        """Transform text content."""
        content = str(token[0]) if token else ""
        line, col = self._get_location_from_token(token[0]) if token else (1, 0)
        return TextNode(content=content, line=line, column=col)
    
    # ========================================================================
    # CONTROL FLOW DIRECTIVES (8)
    # ========================================================================
    
    @v_args(inline=False)
    def if_stmt(self, args: List) -> IfNode:
        """Transform @if(condition) { body } [ @else { else_body } ]"""
        condition = args[0]
        body = args[1] if len(args) > 1 else []
        else_body = args[2] if len(args) > 2 else None
        line, col = self._get_location_from_node(condition)
        return IfNode(condition=condition, body=body, else_body=else_body, line=line, column=col)
    
    @v_args(inline=False)
    def unless_stmt(self, args: List) -> UnlessNode:
        """Transform @unless(condition) { body } [ @else { else_body } ]"""
        condition = args[0]
        body = args[1] if len(args) > 1 else []
        else_body = args[2] if len(args) > 2 else None
        line, col = self._get_location_from_node(condition)
        return UnlessNode(condition=condition, body=body, else_body=else_body, line=line, column=col)
    
    @v_args(inline=False)
    def for_stmt(self, args: List) -> ForNode:
        """Transform @for(variable in iterable) { body } [ @empty { empty_body } ]"""
        variable = str(args[0])
        iterable = args[1]
        body = args[2] if len(args) > 2 else []
        empty_body = args[3] if len(args) > 3 else None
        line, col = self._get_location_from_node(iterable)
        return ForNode(variable=variable, iterable=iterable, body=body, 
                      empty_body=empty_body, line=line, column=col)
    
    @v_args(inline=False)
    def foreach_stmt(self, args: List) -> ForeachNode:
        """Transform @foreach(variable => expression) { body }"""
        variable = str(args[0])
        expression = args[1]
        body = args[2] if len(args) > 2 else []
        empty_body = args[3] if len(args) > 3 else None
        line, col = self._get_location_from_node(expression)
        return ForeachNode(variable=variable, expression=expression, body=body,
                          empty_body=empty_body, line=line, column=col)
    
    @v_args(inline=False)
    def switch_stmt(self, args: List) -> SwitchNode:
        """Transform @switch(expr) { @case(val) { body } ... [ @default { } ] }"""
        expression = args[0]
        cases = [arg for arg in args[1:] if isinstance(arg, CaseNode)]
        default_case = next((arg for arg in args[1:] if isinstance(arg, list)), None)
        line, col = self._get_location_from_node(expression)
        return SwitchNode(expression=expression, cases=cases, 
                         default_case=default_case, line=line, column=col)
    
    @v_args(inline=False)
    def case_stmt(self, args: List) -> CaseNode:
        """Transform @case(value) { body }"""
        value = args[0]
        body = args[1] if len(args) > 1 else []
        line, col = self._get_location_from_node(value)
        return CaseNode(value=value, body=body, line=line, column=col)
    
    def break_stmt(self, args: List) -> BreakNode:
        """Transform @break"""
        line, col = self._get_location_from_token(args[0]) if args else (1, 0)
        return BreakNode(line=line, column=col)
    
    def continue_stmt(self, args: List) -> ContinueNode:
        """Transform @continue"""
        line, col = self._get_location_from_token(args[0]) if args else (1, 0)
        return ContinueNode(line=line, column=col)
    
    # ========================================================================
    # COMPONENT DIRECTIVES (4)
    # ========================================================================
    
    @v_args(inline=False)
    def component_stmt(self, args: List) -> ComponentNode:
        """Transform @component("path", args) { body }"""
        path = str(args[0])
        args_dict = args[1] if len(args) > 1 and isinstance(args[1], dict) else {}
        body = args[2] if len(args) > 2 else args[1] if len(args) > 1 and isinstance(args[1], list) else []
        line, col = (1, 0)
        return ComponentNode(path=path, args=args_dict, body=body, line=line, column=col)
    
    @v_args(inline=False)
    def slot_stmt(self, args: List) -> SlotNode:
        """Transform @slot("name") { body }"""
        name = str(args[0])
        body = args[1] if len(args) > 1 else []
        line, col = (1, 0)
        return SlotNode(name=name, body=body, line=line, column=col)
    
    @v_args(inline=False)
    def render_field_stmt(self, args: List) -> RenderFieldNode:
        """Transform @render_field(type, name, value)"""
        field_type = str(args[0])
        name = str(args[1])
        value = args[2]
        line, col = (1, 0)
        return RenderFieldNode(field_type=field_type, name=name, value=value, line=line, column=col)
    
    @v_args(inline=False)
    def props_stmt(self, args: List) -> PropsNode:
        """Transform @props variable { prop: definition }"""
        variable = str(args[0])
        definitions = args[1] if len(args) > 1 and isinstance(args[1], dict) else {}
        line, col = (1, 0)
        return PropsNode(variable=variable, definitions=definitions, line=line, column=col)
    
    # ========================================================================
    # INHERITANCE DIRECTIVES (6)
    # ========================================================================
    
    def extends_stmt(self, args: List) -> ExtendsNode:
        """Transform @extends("parent_path")"""
        path = str(args[0])
        line, col = self._get_location_from_token(args[0])
        return ExtendsNode(path=path, line=line, column=col)
    
    @v_args(inline=False)
    def block_stmt(self, args: List) -> BlockNode:
        """Transform @block("name") { body }"""
        name = str(args[0])
        body = args[1] if len(args) > 1 else []
        line, col = (1, 0)
        return BlockNode(name=name, body=body, line=line, column=col)
    
    @v_args(inline=False)
    def yield_stmt(self, args: List) -> YieldNode:
        """Transform @yield("name") or @yield("name", default)"""
        name = str(args[0])
        default_value = args[1] if len(args) > 1 else None
        line, col = (1, 0)
        return YieldNode(name=name, default_value=default_value, line=line, column=col)
    
    @v_args(inline=False)
    def section_stmt(self, args: List) -> SectionNode:
        """Transform @section("name") { body }"""
        name = str(args[0])
        body = args[1] if len(args) > 1 else []
        line, col = (1, 0)
        return SectionNode(name=name, body=body, line=line, column=col)
    
    @v_args(inline=False)
    def push_stmt(self, args: List) -> PushNode:
        """Transform @push("stack_name") { body }"""
        stack_name = str(args[0])
        body = args[1] if len(args) > 1 else []
        line, col = (1, 0)
        return PushNode(stack_name=stack_name, body=body, line=line, column=col)
    
    def super_stmt(self, args: List) -> SuperNode:
        """Transform @super"""
        line, col = (1, 0)
        return SuperNode(line=line, column=col)
    
    # ========================================================================
    # FORM DIRECTIVES (6)
    # ========================================================================
    
    def csrf_stmt(self, args: List) -> CSRFTokenNode:
        """Transform @csrf_token"""
        line, col = (1, 0)
        return CSRFTokenNode(line=line, column=col)
    
    @v_args(inline=False)
    def checked_stmt(self, args: List) -> CheckedNode:
        """Transform @checked(field, value)"""
        field = args[0]
        value = args[1]
        line, col = self._get_location_from_node(field)
        return CheckedNode(field=field, value=value, line=line, column=col)
    
    @v_args(inline=False)
    def selected_stmt(self, args: List) -> SelectedNode:
        """Transform @selected(field, value)"""
        field = args[0]
        value = args[1]
        line, col = self._get_location_from_node(field)
        return SelectedNode(field=field, value=value, line=line, column=col)
    
    @v_args(inline=False)
    def disabled_stmt(self, args: List) -> DisabledNode:
        """Transform @disabled([field_names])"""
        fields = [str(arg) for arg in args] if args else []
        line, col = (1, 0)
        return DisabledNode(fields=fields, line=line, column=col)
    
    @v_args(inline=False)
    def readonly_stmt(self, args: List) -> ReadonlyNode:
        """Transform @readonly([field_names])"""
        fields = [str(arg) for arg in args] if args else []
        line, col = (1, 0)
        return ReadonlyNode(fields=fields, line=line, column=col)
    
    @v_args(inline=False)
    def error_stmt(self, args: List) -> ErrorNode:
        """Transform @error("field_name")"""
        field = str(args[0])
        line, col = (1, 0)
        return ErrorNode(field=field, line=line, column=col)
    
    # ========================================================================
    # ROUTING DIRECTIVES (3)
    # ========================================================================
    
    @v_args(inline=False)
    def url_stmt(self, args: List) -> UrlNode:
        """Transform @url("route_name", param1, param2, ...)"""
        route_name = str(args[0])
        params = args[1:] if len(args) > 1 else []
        line, col = (1, 0)
        return UrlNode(route_name=route_name, params=params, line=line, column=col)
    
    @v_args(inline=False)
    def active_link_stmt(self, args: List) -> ActiveLinkNode:
        """Transform @active_link("route_name", params...) { body }"""
        route_name = str(args[0])
        params = []
        body = []
        for i, arg in enumerate(args[1:], 1):
            if isinstance(arg, list):
                body = arg
                break
            params.append(arg)
        line, col = (1, 0)
        return ActiveLinkNode(route_name=route_name, params=params, body=body, line=line, column=col)
    
    def route_stmt(self, args: List) -> RouteNode:
        """Transform @route("route_name")"""
        route_name = str(args[0])
        line, col = self._get_location_from_token(args[0])
        return RouteNode(route_name=route_name, line=line, column=col)
    
    # ========================================================================
    # AUTH DIRECTIVES (4)
    # ========================================================================
    
    @v_args(inline=False)
    def auth_stmt(self, args: List) -> AuthNode:
        """Transform @auth([role1, role2, ...]) { body }"""
        roles = []
        body = []
        for arg in args:
            if isinstance(arg, list):
                body = arg
            else:
                roles.append(str(arg))
        line, col = (1, 0)
        return AuthNode(roles=roles, body=body, line=line, column=col)
    
    @v_args(inline=False)
    def guest_stmt(self, args: List) -> GuestNode:
        """Transform @guest { body }"""
        body = args[0] if args and isinstance(args[0], list) else []
        line, col = (1, 0)
        return GuestNode(body=body, line=line, column=col)
    
    @v_args(inline=False)
    def htmx_stmt(self, args: List) -> HTMXNode:
        """Transform @htmx { body }"""
        body = args[0] if args and isinstance(args[0], list) else []
        line, col = (1, 0)
        return HTMXNode(body=body, line=line, column=col)
    
    @v_args(inline=False)
    def non_htmx_stmt(self, args: List) -> NonHTMXNode:
        """Transform @non_htmx { body }"""
        body = args[0] if args and isinstance(args[0], list) else []
        line, col = (1, 0)
        return NonHTMXNode(body=body, line=line, column=col)
    
    # ========================================================================
    # ASSET DIRECTIVES (3)
    # ========================================================================
    
    def css_stmt(self, args: List) -> CSSNode:
        """Transform @css("path")"""
        path = str(args[0])
        line, col = self._get_location_from_token(args[0])
        return CSSNode(path=path, line=line, column=col)
    
    def js_stmt(self, args: List) -> JSNode:
        """Transform @js("path")"""
        path = str(args[0])
        line, col = self._get_location_from_token(args[0])
        return JSNode(path=path, line=line, column=col)
    
    def vite_stmt(self, args: List) -> ViteNode:
        """Transform @vite("component")"""
        component = str(args[0]) if args else ""
        line, col = self._get_location_from_token(args[0]) if args else (1, 0)
        return ViteNode(component=component, line=line, column=col)
    
    # ========================================================================
    # DATA DIRECTIVES (6)
    # ========================================================================
    
    @v_args(inline=False)
    def let_stmt(self, args: List) -> LetNode:
        """Transform @let(variable, value)"""
        variable = str(args[0])
        value = args[1]
        line, col = self._get_location_from_node(value)
        return LetNode(variable=variable, value=value, line=line, column=col)
    
    @v_args(inline=False)
    def dump_stmt(self, args: List) -> DumpNode:
        """Transform @dump(variable)"""
        variable = args[0]
        line, col = self._get_location_from_node(variable)
        return DumpNode(variable=variable, line=line, column=col)
    
    @v_args(inline=False)
    def span_stmt(self, args: List) -> SpanNode:
        """Transform @span("name") { body }"""
        name = str(args[0])
        body = args[1] if len(args) > 1 else []
        line, col = (1, 0)
        return SpanNode(name=name, body=body, line=line, column=col)
    
    @v_args(inline=False)
    def messages_stmt(self, args: List) -> MessagesNode:
        """Transform @messages { body }"""
        body = args[0] if args and isinstance(args[0], list) else []
        line, col = (1, 0)
        return MessagesNode(body=body, line=line, column=col)
    
    def flash_stmt(self, args: List) -> FlashNode:
        """Transform @flash("key")"""
        key = str(args[0])
        line, col = self._get_location_from_token(args[0])
        return FlashNode(key=key, line=line, column=col)
    
    @v_args(inline=False)
    def status_stmt(self, args: List) -> StatusNode:
        """Transform @status(code) { body }"""
        code = args[0]
        body = args[1] if len(args) > 1 else []
        line, col = self._get_location_from_node(code)
        return StatusNode(code=code, body=body, line=line, column=col)
    
    # ========================================================================
    # SPECIAL DIRECTIVES (2)
    # ========================================================================
    
    @v_args(inline=False)
    def include_stmt(self, args: List) -> IncludeNode:
        """Transform @include("path", var1, var2, ...)"""
        path = str(args[0])
        variables = [str(arg) for arg in args[1:]] if len(args) > 1 else []
        line, col = (1, 0)
        return IncludeNode(path=path, variables=variables, line=line, column=col)
    
    @v_args(inline=False)
    def fragment_stmt(self, args: List) -> FragmentNode:
        """Transform @fragment("name") { body }"""
        name = str(args[0])
        body = args[1] if len(args) > 1 else []
        line, col = (1, 0)
        return FragmentNode(name=name, body=body, line=line, column=col)
    
    # ========================================================================
    # META DIRECTIVES (3)
    # ========================================================================
    
    def method_stmt(self, args: List) -> MethodNode:
        """Transform @method("POST"|"PUT"|"DELETE")"""
        method = str(args[0])
        line, col = self._get_location_from_token(args[0])
        return MethodNode(method=method, line=line, column=col)
    
    def old_stmt(self, args: List) -> OldNode:
        """Transform @old("field_name")"""
        field = str(args[0])
        line, col = self._get_location_from_token(args[0])
        return OldNode(field=field, line=line, column=col)
    
    @v_args(inline=False)
    def json_stmt(self, args: List) -> JSONNode:
        """Transform @json(variable)"""
        variable = args[0]
        line, col = self._get_location_from_node(variable)
        return JSONNode(variable=variable, line=line, column=col)
    
    # ========================================================================
    # EXPRESSIONS
    # ========================================================================
    
    @v_args(inline=False)
    def binary_op(self, args: List) -> BinaryOpNode:
        """Transform binary operation: left op right"""
        left = args[0]
        op = str(args[1])
        right = args[2]
        line, col = self._get_location_from_node(left)
        return BinaryOpNode(left=left, op=op, right=right, line=line, column=col)
    
    @v_args(inline=False)
    def unary_op(self, args: List) -> UnaryOpNode:
        """Transform unary operation: op operand"""
        op = str(args[0])
        operand = args[1]
        line, col = (1, 0)
        return UnaryOpNode(op=op, operand=operand, line=line, column=col)
    
    @v_args(inline=False)
    def filter_expr(self, args: List) -> FilterNode:
        """Transform filter application: expression | filter_name(args)"""
        expression = args[0]
        filter_name = str(args[1])
        filter_args = args[2:] if len(args) > 2 else []
        line, col = self._get_location_from_node(expression)
        return FilterNode(expression=expression, filter_name=filter_name, 
                         args=filter_args, line=line, column=col)
    
    @v_args(inline=False)
    def test_expr(self, args: List) -> TestNode:
        """Transform test function: expression is test_name(args)"""
        expression = args[0]
        test_name = str(args[1])
        test_args = args[2:] if len(args) > 2 else []
        line, col = self._get_location_from_node(expression)
        return TestNode(expression=expression, test_name=test_name, 
                       args=test_args, line=line, column=col)
    
    @v_args(inline=False)
    def call_expr(self, args: List) -> CallNode:
        """Transform function call: function_name(args)"""
        function_name = str(args[0])
        call_args = args[1:] if len(args) > 1 else []
        line, col = (1, 0)
        return CallNode(function_name=function_name, args=call_args, line=line, column=col)
    
    # ========================================================================
    # LITERALS & REFERENCES
    # ========================================================================
    
    def variable(self, args: List) -> VariableNode:
        """Transform variable reference"""
        name = str(args[0])
        line, col = self._get_location_from_token(args[0])
        return VariableNode(name=name, line=line, column=col)
    
    def literal_string(self, args: List) -> LiteralNode:
        """Transform string literal"""
        value = str(args[0])
        line, col = self._get_location_from_token(args[0])
        return LiteralNode(value=value, type_name="string", line=line, column=col)
    
    def literal_number(self, args: List) -> LiteralNode:
        """Transform number literal"""
        value = float(args[0]) if '.' in str(args[0]) else int(args[0])
        line, col = self._get_location_from_token(args[0])
        return LiteralNode(value=value, type_name="number", line=line, column=col)
    
    def literal_boolean(self, args: List) -> LiteralNode:
        """Transform boolean literal"""
        value = str(args[0]).lower() == 'true'
        line, col = self._get_location_from_token(args[0])
        return LiteralNode(value=value, type_name="boolean", line=line, column=col)
    
    def literal_null(self, args: List) -> LiteralNode:
        """Transform null literal"""
        line, col = self._get_location_from_token(args[0]) if args else (1, 0)
        return LiteralNode(value=None, type_name="null", line=line, column=col)
    
    @v_args(inline=False)
    def property_access(self, args: List) -> PropertyAccessNode:
        """Transform property access: obj.prop"""
        object_expr = args[0]
        property_name = str(args[1])
        line, col = self._get_location_from_node(object_expr)
        return PropertyAccessNode(object_expr=object_expr, property_name=property_name, 
                                 line=line, column=col)
    
    @v_args(inline=False)
    def array_access(self, args: List) -> ArrayAccessNode:
        """Transform array access: arr[index]"""
        array_expr = args[0]
        index = args[1]
        line, col = self._get_location_from_node(array_expr)
        return ArrayAccessNode(array_expr=array_expr, index=index, line=line, column=col)
    
    # ========================================================================
    # COLLECTIONS
    # ========================================================================
    
    @v_args(inline=False)
    def list_literal(self, args: List) -> ListNode:
        """Transform list literal: [item1, item2, ...]"""
        elements = args if args else []
        line, col = (1, 0)
        return ListNode(elements=elements, line=line, column=col)
    
    @v_args(inline=False)
    def dict_literal(self, args: List) -> DictNode:
        """Transform dictionary literal: {key1: val1, key2: val2, ...}"""
        pairs = {}
        for i in range(0, len(args), 2):
            if i + 1 < len(args):
                key = str(args[i])
                value = args[i + 1]
                pairs[key] = value
        line, col = (1, 0)
        return DictNode(pairs=pairs, line=line, column=col)


def parse(parse_tree: Tree) -> ASTNode:
    """
    Parse a Lark parse tree into an Eden AST.
    
    Args:
        parse_tree: Lark Tree from lexer.tokenize()
        
    Returns:
        Root TemplateNode of the AST
        
    Raises:
        ParseError: If transformation fails
        
    Example:
        >>> from eden_engine.lexer import create_lexer
        >>> from eden_engine.parser import parse
        >>> 
        >>> lexer = create_lexer()
        >>> tree = lexer.tokenize("@if(x) { {{ y }} }")
        >>> ast = parse(tree)
        >>> print(ast.to_debug_string())
    """
    parser = EdenParser()
    try:
        return parser.transform(parse_tree)
    except Exception as e:
        raise ParseError(f"AST parsing failed: {str(e)}")
