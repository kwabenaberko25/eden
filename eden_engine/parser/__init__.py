"""
Eden Templating Engine - Parser Module

Transforms Lark parse trees into structured AST nodes.

This module provides:
  1. AST Node Types: 50+ node classes representing template structures
  2. Parser: EdenParser (Lark Transformer) for tree transformation
  3. Parse Function: Quick interface for parsing

AST Node Categories:
  - Collection: TemplateNode, TextNode
  - Control Flow: IfNode, UnlessNode, ForNode, ForeachNode, SwitchNode, CaseNode, BreakNode, ContinueNode
  - Components: ComponentNode, SlotNode, RenderFieldNode, PropsNode
  - Inheritance: ExtendsNode, BlockNode, YieldNode, SectionNode, PushNode, SuperNode
  - Forms: CSRFTokenNode, CheckedNode, SelectedNode, DisabledNode, ReadonlyNode, ErrorNode
  - Routing: UrlNode, ActiveLinkNode, RouteNode
  - Auth: AuthNode, GuestNode, HTMXNode, NonHTMXNode
  - Assets: CSSNode, JSNode, ViteNode
  - Data: LetNode, DumpNode, SpanNode, MessagesNode, FlashNode, StatusNode
  - Special: IncludeNode, FragmentNode
  - Meta: MethodNode, OldNode, JSONNode
  - Expressions: BinaryOpNode, UnaryOpNode, FilterNode, TestNode, CallNode
  - Literals: VariableNode, LiteralNode, PropertyAccessNode, ArrayAccessNode
  - Collections: ListNode, DictNode

Key Classes:
  - ASTNode: Base class for all nodes (visitor pattern, line/column tracking)
  - ASTVisitor: Visitor interface for AST traversal (abstract)
  - DefaultASTVisitor: Default visitor implementation with generic traversal
  - EdenParser: Lark Transformer for parsing trees -> AST
  - ParseError: Exception for parser failures

Usage Example:
    from eden_engine.lexer import create_lexer
    from eden_engine.parser import parse, ParseError, IfNode
    
    lexer = create_lexer()
    tree = lexer.tokenize("@if(x > 5) { {{ y }} }")
    
    try:
        ast = parse(tree)
        print(ast.to_debug_string())
    except ParseError as e:
        print(f"Parse error: {e}")
    
    # Or use custom visitor
    from eden_engine.parser import DefaultASTVisitor
    
    class MyVisitor(DefaultASTVisitor):
        def visit_if(self, node: IfNode):
            print(f"Found if node with condition")
            return super().visit_if(node)
    
    visitor = MyVisitor()
    ast.accept(visitor)
"""

from .ast_nodes import (
    # Base
    ASTNode,
    ASTVisitor,
    DefaultASTVisitor,
    # Collection
    TemplateNode,
    TextNode,
    # Control Flow
    IfNode,
    UnlessNode,
    ForNode,
    ForeachNode,
    SwitchNode,
    CaseNode,
    BreakNode,
    ContinueNode,
    # Components
    ComponentNode,
    SlotNode,
    RenderFieldNode,
    PropsNode,
    # Inheritance
    ExtendsNode,
    BlockNode,
    YieldNode,
    SectionNode,
    PushNode,
    SuperNode,
    # Forms
    CSRFTokenNode,
    CheckedNode,
    SelectedNode,
    DisabledNode,
    ReadonlyNode,
    ErrorNode,
    # Routing
    UrlNode,
    ActiveLinkNode,
    RouteNode,
    # Auth
    AuthNode,
    GuestNode,
    HTMXNode,
    NonHTMXNode,
    # Assets
    CSSNode,
    JSNode,
    ViteNode,
    # Data
    LetNode,
    DumpNode,
    SpanNode,
    MessagesNode,
    FlashNode,
    StatusNode,
    # Special
    IncludeNode,
    FragmentNode,
    # Meta
    MethodNode,
    OldNode,
    JSONNode,
    # Expressions
    BinaryOpNode,
    UnaryOpNode,
    FilterNode,
    TestNode,
    CallNode,
    # Literals
    VariableNode,
    LiteralNode,
    PropertyAccessNode,
    ArrayAccessNode,
    # Collections
    ListNode,
    DictNode,
)

from .parser import (
    EdenParser,
    parse,
    ParseError,
)

__all__ = [
    # Base
    'ASTNode',
    'ASTVisitor',
    'DefaultASTVisitor',
    # Parser
    'EdenParser',
    'parse',
    'ParseError',
    # Collection
    'TemplateNode',
    'TextNode',
    # Control Flow
    'IfNode',
    'UnlessNode',
    'ForNode',
    'ForeachNode',
    'SwitchNode',
    'CaseNode',
    'BreakNode',
    'ContinueNode',
    # Components
    'ComponentNode',
    'SlotNode',
    'RenderFieldNode',
    'PropsNode',
    # Inheritance
    'ExtendsNode',
    'BlockNode',
    'YieldNode',
    'SectionNode',
    'PushNode',
    'SuperNode',
    # Forms
    'CSRFTokenNode',
    'CheckedNode',
    'SelectedNode',
    'DisabledNode',
    'ReadonlyNode',
    'ErrorNode',
    # Routing
    'UrlNode',
    'ActiveLinkNode',
    'RouteNode',
    # Auth
    'AuthNode',
    'GuestNode',
    'HTMXNode',
    'NonHTMXNode',
    # Assets
    'CSSNode',
    'JSNode',
    'ViteNode',
    # Data
    'LetNode',
    'DumpNode',
    'SpanNode',
    'MessagesNode',
    'FlashNode',
    'StatusNode',
    # Special
    'IncludeNode',
    'FragmentNode',
    # Meta
    'MethodNode',
    'OldNode',
    'JSONNode',
    # Expressions
    'BinaryOpNode',
    'UnaryOpNode',
    'FilterNode',
    'TestNode',
    'CallNode',
    # Literals
    'VariableNode',
    'LiteralNode',
    'PropertyAccessNode',
    'ArrayAccessNode',
    # Collections
    'ListNode',
    'DictNode',
]