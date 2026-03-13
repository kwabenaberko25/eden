"""
Eden Templating Engine - Abstract Syntax Tree (AST) Node Definitions

This module defines all AST node types for the Eden templating language.
Supports 50+ directive types organized by category, with visitor pattern
for clean traversal and transformation.

Node Categories:
  - Collection (2): Template, Text
  - Control Flow (7): if, unless, for, foreach, switch, break, continue
  - Components (4): component, slot, render_field, props
  - Inheritance (6): extends, block, yield, section, push, super
  - Forms (6): csrf, checked, selected, disabled, readonly, error
  - Routing (3): url, active_link, route
  - Auth (4): auth, guest, htmx, non_htmx
  - Assets (3): css, js, vite
  - Data (6): let, dump, span, messages, flash, status
  - Special (2): include, fragment
  - Meta (3): method, old, json
  - Expressions (5): binary_op, unary_op, filter, test, call
  - Literals (4): variable, literal, list, dict
  - Access (2): property_access, array_access

Total: 50+ node types for complete Eden template AST coverage.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union
from enum import Enum


class ASTNode(ABC):
    """
    Abstract base class for all AST nodes.
    
    Implements visitor pattern for clean traversal and transformation.
    All nodes track source location (line/column) for error reporting.
    """
    
    def __init__(self, line: int = 0, column: int = 0):
        """
        Initialize AST node with source location.
        
        Args:
            line: Line number in source template (1-indexed)
            column: Column number in source template (0-indexed)
        """
        self.line = line
        self.column = column
        self.children: List['ASTNode'] = []
        self.parent: Optional['ASTNode'] = None
    
    @abstractmethod
    def accept(self, visitor: 'ASTVisitor') -> Any:
        """
        Accept a visitor for traversal/transformation (visitor pattern).
        
        Args:
            visitor: ASTVisitor instance implementing visit_* methods
            
        Returns:
            Visitor-dependent result
        """
        pass
    
    def add_child(self, child: 'ASTNode') -> None:
        """Register a child node."""
        if child is not None:
            self.children.append(child)
            child.parent = self
    
    def add_children(self, children: Optional[List['ASTNode']]) -> None:
        """Register multiple child nodes."""
        if children:
            for child in children:
                self.add_child(child)
    
    def get_source_location(self) -> str:
        """Get formatted source location for error messages."""
        return f"Line {self.line}, Column {self.column}"
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(line={self.line}, col={self.column})"
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize node to dictionary for debugging."""
        return {
            'type': self.__class__.__name__,
            'line': self.line,
            'column': self.column,
            'children': len(self.children)
        }
    
    def to_debug_string(self, indent: int = 0) -> str:
        """Pretty-print AST for inspection."""
        prefix = "  " * indent
        result = f"{prefix}{self.__class__.__name__}\n"
        for child in self.children:
            if hasattr(child, 'to_debug_string'):
                result += child.to_debug_string(indent + 1)
        return result




# ============================================================================
# COLLECTION NODES (2)
# ============================================================================

class TemplateNode(ASTNode):
    """Root node representing entire template."""
    
    def __init__(self, statements: Optional[List[ASTNode]] = None,
                 line: int = 0, column: int = 0):
        super().__init__(line, column)
        self.statements = statements or []
        self.add_children(self.statements)
    
    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_template(self)


class TextNode(ASTNode):
    """Literal text content (between directives)."""
    
    def __init__(self, content: str, line: int = 0, column: int = 0):
        super().__init__(line, column)
        self.content = content
    
    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_text(self)


# ============================================================================
# CONTROL FLOW NODES (7)
# ============================================================================

class IfNode(ASTNode):
    """@if(condition) { body }"""
    
    def __init__(self, condition: ASTNode, body: Optional[List[ASTNode]] = None,
                 else_body: Optional[List[ASTNode]] = None,
                 line: int = 0, column: int = 0):
        super().__init__(line, column)
        self.condition = condition
        self.body = body or []
        self.else_body = else_body
        self.add_child(self.condition)
        self.add_children(self.body)
        if self.else_body:
            self.add_children(self.else_body)
    
    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_if(self)


class UnlessNode(ASTNode):
    """@unless(condition) { body } - inverse of if"""
    
    def __init__(self, condition: ASTNode, body: Optional[List[ASTNode]] = None,
                 else_body: Optional[List[ASTNode]] = None,
                 line: int = 0, column: int = 0):
        super().__init__(line, column)
        self.condition = condition
        self.body = body or []
        self.else_body = else_body
        self.add_child(self.condition)
        self.add_children(self.body)
        if self.else_body:
            self.add_children(self.else_body)
    
    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_unless(self)


class ForNode(ASTNode):
    """@for(variable in iterable) { body }"""
    
    def __init__(self, variable: str, iterable: ASTNode,
                 body: Optional[List[ASTNode]] = None,
                 empty_body: Optional[List[ASTNode]] = None,
                 line: int = 0, column: int = 0):
        super().__init__(line, column)
        self.variable = variable
        self.iterable = iterable
        self.body = body or []
        self.empty_body = empty_body
        self.add_child(self.iterable)
        self.add_children(self.body)
        if self.empty_body:
            self.add_children(self.empty_body)
    
    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_for(self)


class ForeachNode(ASTNode):
    """@foreach(variable => expression) { body }"""
    
    def __init__(self, variable: str, expression: ASTNode,
                 body: Optional[List[ASTNode]] = None,
                 empty_body: Optional[List[ASTNode]] = None,
                 line: int = 0, column: int = 0):
        super().__init__(line, column)
        self.variable = variable
        self.expression = expression
        self.body = body or []
        self.empty_body = empty_body
        self.add_child(self.expression)
        self.add_children(self.body)
        if self.empty_body:
            self.add_children(self.empty_body)
    
    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_foreach(self)


class SwitchNode(ASTNode):
    """@switch(expr) { @case(val) { } @case(...) { } }"""
    
    def __init__(self, expression: ASTNode, cases: Optional[List['CaseNode']] = None,
                 default_case: Optional[List[ASTNode]] = None,
                 line: int = 0, column: int = 0):
        super().__init__(line, column)
        self.expression = expression
        self.cases = cases or []
        self.default_case = default_case
        self.add_child(self.expression)
        self.add_children(self.cases)
        if self.default_case:
            self.add_children(self.default_case)
    
    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_switch(self)


class CaseNode(ASTNode):
    """@case(value) { body } - within @switch"""
    
    def __init__(self, value: ASTNode, body: Optional[List[ASTNode]] = None,
                 line: int = 0, column: int = 0):
        super().__init__(line, column)
        self.value = value
        self.body = body or []
        self.add_child(self.value)
        self.add_children(self.body)
    
    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_case(self)


class BreakNode(ASTNode):
    """@break - exit loop"""
    
    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_break(self)


class ContinueNode(ASTNode):
    """@continue - skip to next iteration"""
    
    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_continue(self)


# ============================================================================
# COMPONENT NODES (4)
# ============================================================================

class ComponentNode(ASTNode):
    """@component("path", args) { body }"""
    
    def __init__(self, path: str, args: Optional[Dict[str, ASTNode]] = None,
                 body: Optional[List[ASTNode]] = None,
                 line: int = 0, column: int = 0):
        super().__init__(line, column)
        self.path = path
        self.args = args or {}
        self.body = body or []
        for arg_expr in self.args.values():
            self.add_child(arg_expr)
        self.add_children(self.body)
    
    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_component(self)


class SlotNode(ASTNode):
    """@slot("name") { default_content }"""
    
    def __init__(self, name: str, body: Optional[List[ASTNode]] = None,
                 line: int = 0, column: int = 0):
        super().__init__(line, column)
        self.name = name
        self.body = body or []
        self.add_children(self.body)
    
    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_slot(self)


class RenderFieldNode(ASTNode):
    """@render_field(type, name, value)"""
    
    def __init__(self, field_type: str, name: str, value: ASTNode,
                 line: int = 0, column: int = 0):
        super().__init__(line, column)
        self.field_type = field_type
        self.name = name
        self.value = value
        self.add_child(self.value)
    
    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_render_field(self)


class PropsNode(ASTNode):
    """@props variable { prop: definition }"""
    
    def __init__(self, variable: str, definitions: Optional[Dict[str, ASTNode]] = None,
                 line: int = 0, column: int = 0):
        super().__init__(line, column)
        self.variable = variable
        self.definitions = definitions or {}
        for def_expr in self.definitions.values():
            self.add_child(def_expr)
    
    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_props(self)


# ============================================================================
# INHERITANCE NODES (6)
# ============================================================================

class ExtendsNode(ASTNode):
    """@extends("parent_template_path")"""
    
    def __init__(self, path: str, line: int = 0, column: int = 0):
        super().__init__(line, column)
        self.path = path
    
    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_extends(self)


class BlockNode(ASTNode):
    """@block("name") { content_to_override }"""
    
    def __init__(self, name: str, body: Optional[List[ASTNode]] = None,
                 line: int = 0, column: int = 0):
        super().__init__(line, column)
        self.name = name
        self.body = body or []
        self.add_children(self.body)
    
    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_block(self)


class YieldNode(ASTNode):
    """@yield("block_name") or @yield("block_name", default_value)"""
    
    def __init__(self, name: str, default_value: Optional[ASTNode] = None,
                 line: int = 0, column: int = 0):
        super().__init__(line, column)
        self.name = name
        self.default_value = default_value
        if self.default_value:
            self.add_child(self.default_value)
    
    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_yield(self)


class SectionNode(ASTNode):
    """@section("name") { content }"""
    
    def __init__(self, name: str, body: Optional[List[ASTNode]] = None,
                 line: int = 0, column: int = 0):
        super().__init__(line, column)
        self.name = name
        self.body = body or []
        self.add_children(self.body)
    
    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_section(self)


class PushNode(ASTNode):
    """@push("stack_name") { content }"""
    
    def __init__(self, stack_name: str, body: Optional[List[ASTNode]] = None,
                 line: int = 0, column: int = 0):
        super().__init__(line, column)
        self.stack_name = stack_name
        self.body = body or []
        self.add_children(self.body)
    
    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_push(self)


class SuperNode(ASTNode):
    """@super - render parent block content"""
    
    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_super(self)





# ============================================================================
# FORM NODES (6)
# ============================================================================

class CSRFTokenNode(ASTNode):
    """@csrf_token - insert CSRF protection field"""
    
    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_csrf_token(self)


class CheckedNode(ASTNode):
    """@checked(field, value) - conditionally render checked attribute"""
    
    def __init__(self, field: ASTNode, value: ASTNode,
                 line: int = 0, column: int = 0):
        super().__init__(line, column)
        self.field = field
        self.value = value
        self.add_child(self.field)
        self.add_child(self.value)
    
    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_checked(self)


class SelectedNode(ASTNode):
    """@selected(field, value) - conditionally render selected attribute"""
    
    def __init__(self, field: ASTNode, value: ASTNode,
                 line: int = 0, column: int = 0):
        super().__init__(line, column)
        self.field = field
        self.value = value
        self.add_child(self.field)
        self.add_child(self.value)
    
    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_selected(self)


class DisabledNode(ASTNode):
    """@disabled([field_names]) - disable form fields"""
    
    def __init__(self, fields: Optional[List[str]] = None,
                 line: int = 0, column: int = 0):
        super().__init__(line, column)
        self.fields = fields or []
    
    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_disabled(self)


class ReadonlyNode(ASTNode):
    """@readonly([field_names]) - make form fields readonly"""
    
    def __init__(self, fields: Optional[List[str]] = None,
                 line: int = 0, column: int = 0):
        super().__init__(line, column)
        self.fields = fields or []
    
    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_readonly(self)


class ErrorNode(ASTNode):
    """@error("field_name") - display validation error"""
    
    def __init__(self, field: str, line: int = 0, column: int = 0):
        super().__init__(line, column)
        self.field = field
    
    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_error(self)


# ============================================================================
# ROUTING NODES (3)
# ============================================================================

class UrlNode(ASTNode):
    """@url("route_name", param1, param2, ...)"""
    
    def __init__(self, route_name: str, params: Optional[List[ASTNode]] = None,
                 line: int = 0, column: int = 0):
        super().__init__(line, column)
        self.route_name = route_name
        self.params = params or []
        self.add_children(self.params)
    
    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_url(self)


class ActiveLinkNode(ASTNode):
    """@active_link("route_name", params...) { content }"""
    
    def __init__(self, route_name: str, params: Optional[List[ASTNode]] = None,
                 body: Optional[List[ASTNode]] = None,
                 line: int = 0, column: int = 0):
        super().__init__(line, column)
        self.route_name = route_name
        self.params = params or []
        self.body = body or []
        self.add_children(self.params)
        self.add_children(self.body)
    
    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_active_link(self)


class RouteNode(ASTNode):
    """@route("route_name")"""
    
    def __init__(self, route_name: str, line: int = 0, column: int = 0):
        super().__init__(line, column)
        self.route_name = route_name
    
    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_route(self)


# ============================================================================
# AUTH/VISIBILITY NODES (4)
# ============================================================================

class AuthNode(ASTNode):
    """@auth([role1, role2, ...]) { content }"""
    
    def __init__(self, roles: Optional[List[str]] = None,
                 body: Optional[List[ASTNode]] = None,
                 line: int = 0, column: int = 0):
        super().__init__(line, column)
        self.roles = roles or []
        self.body = body or []
        self.add_children(self.body)
    
    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_auth(self)


class GuestNode(ASTNode):
    """@guest { content } - show if not authenticated"""
    
    def __init__(self, body: Optional[List[ASTNode]] = None,
                 line: int = 0, column: int = 0):
        super().__init__(line, column)
        self.body = body or []
        self.add_children(self.body)
    
    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_guest(self)


class HTMXNode(ASTNode):
    """@htmx { content } - show if HTMX request"""
    
    def __init__(self, body: Optional[List[ASTNode]] = None,
                 line: int = 0, column: int = 0):
        super().__init__(line, column)
        self.body = body or []
        self.add_children(self.body)
    
    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_htmx(self)


class NonHTMXNode(ASTNode):
    """@non_htmx { content } - show if NOT HTMX request"""
    
    def __init__(self, body: Optional[List[ASTNode]] = None,
                 line: int = 0, column: int = 0):
        super().__init__(line, column)
        self.body = body or []
        self.add_children(self.body)
    
    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_non_htmx(self)


# ============================================================================
# ASSET NODES (3)
# ============================================================================

class CSSNode(ASTNode):
    """@css("path/to/stylesheet.css")"""
    
    def __init__(self, path: str, line: int = 0, column: int = 0):
        super().__init__(line, column)
        self.path = path
    
    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_css(self)


class JSNode(ASTNode):
    """@js("path/to/script.js")"""
    
    def __init__(self, path: str, line: int = 0, column: int = 0):
        super().__init__(line, column)
        self.path = path
    
    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_js(self)


class ViteNode(ASTNode):
    """@vite("component_name")"""
    
    def __init__(self, component: str, line: int = 0, column: int = 0):
        super().__init__(line, column)
        self.component = component
    
    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_vite(self)


# ============================================================================
# DATA/STATE NODES (6)
# ============================================================================

class LetNode(ASTNode):
    """@let(variable, value) - declare local variable"""
    
    def __init__(self, variable: str, value: ASTNode,
                 line: int = 0, column: int = 0):
        super().__init__(line, column)
        self.variable = variable
        self.value = value
        self.add_child(self.value)
    
    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_let(self)


class DumpNode(ASTNode):
    """@dump(variable) - debug output"""
    
    def __init__(self, variable: ASTNode, line: int = 0, column: int = 0):
        super().__init__(line, column)
        self.variable = variable
        self.add_child(self.variable)
    
    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_dump(self)


class SpanNode(ASTNode):
    """@span("name") { content } - define content region"""
    
    def __init__(self, name: str, body: Optional[List[ASTNode]] = None,
                 line: int = 0, column: int = 0):
        super().__init__(line, column)
        self.name = name
        self.body = body or []
        self.add_children(self.body)
    
    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_span(self)


class MessagesNode(ASTNode):
    """@messages { content } - iterate over messages"""
    
    def __init__(self, body: Optional[List[ASTNode]] = None,
                 line: int = 0, column: int = 0):
        super().__init__(line, column)
        self.body = body or []
        self.add_children(self.body)
    
    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_messages(self)


class FlashNode(ASTNode):
    """@flash("key") - display flash message"""
    
    def __init__(self, key: str, line: int = 0, column: int = 0):
        super().__init__(line, column)
        self.key = key
    
    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_flash(self)


class StatusNode(ASTNode):
    """@status(code) { content } - conditional on HTTP status"""
    
    def __init__(self, code: Union[int, str], body: Optional[List[ASTNode]] = None,
                 line: int = 0, column: int = 0):
        super().__init__(line, column)
        self.code = code
        self.body = body or []
        self.add_children(self.body)
    
    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_status(self)


# ============================================================================
# SPECIAL NODES (2)
# ============================================================================

class IncludeNode(ASTNode):
    """@include("path", var1, var2, ...)"""
    
    def __init__(self, path: str, variables: Optional[List[str]] = None,
                 line: int = 0, column: int = 0):
        super().__init__(line, column)
        self.path = path
        self.variables = variables or []
    
    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_include(self)


class FragmentNode(ASTNode):
    """@fragment("name") { content } - define reusable fragment"""
    
    def __init__(self, name: str, body: Optional[List[ASTNode]] = None,
                 line: int = 0, column: int = 0):
        super().__init__(line, column)
        self.name = name
        self.body = body or []
        self.add_children(self.body)
    
    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_fragment(self)


# ============================================================================
# META NODES (3)
# ============================================================================

class MethodNode(ASTNode):
    """@method("POST"|"PUT"|"DELETE") - HTTP method override"""
    
    def __init__(self, method: str, line: int = 0, column: int = 0):
        super().__init__(line, column)
        self.method = method.upper()
    
    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_method(self)


class OldNode(ASTNode):
    """@old("field_name") - restore old form value after validation error"""
    
    def __init__(self, field: str, line: int = 0, column: int = 0):
        super().__init__(line, column)
        self.field = field
    
    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_old(self)


class JSONNode(ASTNode):
    """@json(variable) - render as JSON"""
    
    def __init__(self, variable: ASTNode, line: int = 0, column: int = 0):
        super().__init__(line, column)
        self.variable = variable
        self.add_child(self.variable)
    
    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_json(self)





# ============================================================================
# EXPRESSION NODES (5)
# ============================================================================

class BinaryOpNode(ASTNode):
    """Binary operation: left op right"""
    
    def __init__(self, left: ASTNode, op: str, right: ASTNode,
                 line: int = 0, column: int = 0):
        super().__init__(line, column)
        self.left = left
        self.op = op
        self.right = right
        self.add_child(self.left)
        self.add_child(self.right)
    
    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_binary_op(self)


class UnaryOpNode(ASTNode):
    """Unary operation: op operand"""
    
    def __init__(self, op: str, operand: ASTNode,
                 line: int = 0, column: int = 0):
        super().__init__(line, column)
        self.op = op
        self.operand = operand
        self.add_child(self.operand)
    
    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_unary_op(self)


class FilterNode(ASTNode):
    """Filter application: expression | filter_name(args)"""
    
    def __init__(self, expression: ASTNode, filter_name: str,
                 args: Optional[List[ASTNode]] = None,
                 line: int = 0, column: int = 0):
        super().__init__(line, column)
        self.expression = expression
        self.filter_name = filter_name
        self.args = args or []
        self.add_child(self.expression)
        self.add_children(self.args)
    
    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_filter(self)


class TestNode(ASTNode):
    """Test function: expression is test_name(args)"""
    
    def __init__(self, expression: ASTNode, test_name: str,
                 args: Optional[List[ASTNode]] = None,
                 line: int = 0, column: int = 0):
        super().__init__(line, column)
        self.expression = expression
        self.test_name = test_name
        self.args = args or []
        self.add_child(self.expression)
        self.add_children(self.args)
    
    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_test(self)


class CallNode(ASTNode):
    """Function call: function_name(args)"""
    
    def __init__(self, function_name: str, args: Optional[List[ASTNode]] = None,
                 line: int = 0, column: int = 0):
        super().__init__(line, column)
        self.function_name = function_name
        self.args = args or []
        self.add_children(self.args)
    
    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_call(self)


# ============================================================================
# LITERAL & REFERENCE NODES (5)
# ============================================================================

class VariableNode(ASTNode):
    """Variable reference: identifier"""
    
    def __init__(self, name: str, line: int = 0, column: int = 0):
        super().__init__(line, column)
        self.name = name
    
    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_variable(self)


class LiteralNode(ASTNode):
    """Literal value: string, number, boolean, null"""
    
    def __init__(self, value: Any, type_name: str = "object",
                 line: int = 0, column: int = 0):
        super().__init__(line, column)
        self.value = value
        self.type_name = type_name  # "string", "number", "boolean", "null"
    
    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_literal(self)


class PropertyAccessNode(ASTNode):
    """Property access: object.property or object[property]"""
    
    def __init__(self, object_expr: ASTNode, property_name: str,
                 line: int = 0, column: int = 0):
        super().__init__(line, column)
        self.object_expr = object_expr
        self.property_name = property_name
        self.add_child(self.object_expr)
    
    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_property_access(self)


class ArrayAccessNode(ASTNode):
    """Array access: array[index]"""
    
    def __init__(self, array_expr: ASTNode, index: ASTNode,
                 line: int = 0, column: int = 0):
        super().__init__(line, column)
        self.array_expr = array_expr
        self.index = index
        self.add_child(self.array_expr)
        self.add_child(self.index)
    
    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_array_access(self)


# ============================================================================
# COLLECTION LITERAL NODES (2)
# ============================================================================

class ListNode(ASTNode):
    """List literal: [item1, item2, ...]"""
    
    def __init__(self, elements: Optional[List[ASTNode]] = None,
                 line: int = 0, column: int = 0):
        super().__init__(line, column)
        self.elements = elements or []
        self.add_children(self.elements)
    
    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_list(self)


class DictNode(ASTNode):
    """Dictionary literal: {key1: value1, key2: value2, ...}"""
    
    def __init__(self, pairs: Optional[Dict[str, ASTNode]] = None,
                 line: int = 0, column: int = 0):
        super().__init__(line, column)
        self.pairs = pairs or {}
        for value in self.pairs.values():
            self.add_child(value)
    
    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_dict(self)





# ============================================================================
# VISITOR INTERFACE
# ============================================================================

class ASTVisitor(ABC):
    """
    Abstract base class for AST visitors (implements visitor pattern).
    
    Subclasses implement specific compilation/analysis strategies:
      - CodeGenerator: AST → Python bytecode
      - Interpreter: AST → Runtime execution
      - Analyzer: AST → Analysis results (type checking, optimization)
      - DebugPrinter: Pretty-print AST for inspection
    """
    
    @abstractmethod
    def visit_template(self, node: TemplateNode) -> Any: pass
    
    @abstractmethod
    def visit_text(self, node: TextNode) -> Any: pass
    
    # Control Flow
    @abstractmethod
    def visit_if(self, node: IfNode) -> Any: pass
    
    @abstractmethod
    def visit_unless(self, node: UnlessNode) -> Any: pass
    
    @abstractmethod
    def visit_for(self, node: ForNode) -> Any: pass
    
    @abstractmethod
    def visit_foreach(self, node: ForeachNode) -> Any: pass
    
    @abstractmethod
    def visit_switch(self, node: SwitchNode) -> Any: pass
    
    @abstractmethod
    def visit_case(self, node: CaseNode) -> Any: pass
    
    @abstractmethod
    def visit_break(self, node: BreakNode) -> Any: pass
    
    @abstractmethod
    def visit_continue(self, node: ContinueNode) -> Any: pass
    
    # Components
    @abstractmethod
    def visit_component(self, node: ComponentNode) -> Any: pass
    
    @abstractmethod
    def visit_slot(self, node: SlotNode) -> Any: pass
    
    @abstractmethod
    def visit_render_field(self, node: RenderFieldNode) -> Any: pass
    
    @abstractmethod
    def visit_props(self, node: PropsNode) -> Any: pass
    
    # Inheritance
    @abstractmethod
    def visit_extends(self, node: ExtendsNode) -> Any: pass
    
    @abstractmethod
    def visit_block(self, node: BlockNode) -> Any: pass
    
    @abstractmethod
    def visit_yield(self, node: YieldNode) -> Any: pass
    
    @abstractmethod
    def visit_section(self, node: SectionNode) -> Any: pass
    
    @abstractmethod
    def visit_push(self, node: PushNode) -> Any: pass
    
    @abstractmethod
    def visit_super(self, node: SuperNode) -> Any: pass
    
    # Forms
    @abstractmethod
    def visit_csrf_token(self, node: CSRFTokenNode) -> Any: pass
    
    @abstractmethod
    def visit_checked(self, node: CheckedNode) -> Any: pass
    
    @abstractmethod
    def visit_selected(self, node: SelectedNode) -> Any: pass
    
    @abstractmethod
    def visit_disabled(self, node: DisabledNode) -> Any: pass
    
    @abstractmethod
    def visit_readonly(self, node: ReadonlyNode) -> Any: pass
    
    @abstractmethod
    def visit_error(self, node: ErrorNode) -> Any: pass
    
    # Routing
    @abstractmethod
    def visit_url(self, node: UrlNode) -> Any: pass
    
    @abstractmethod
    def visit_active_link(self, node: ActiveLinkNode) -> Any: pass
    
    @abstractmethod
    def visit_route(self, node: RouteNode) -> Any: pass
    
    # Auth
    @abstractmethod
    def visit_auth(self, node: AuthNode) -> Any: pass
    
    @abstractmethod
    def visit_guest(self, node: GuestNode) -> Any: pass
    
    @abstractmethod
    def visit_htmx(self, node: HTMXNode) -> Any: pass
    
    @abstractmethod
    def visit_non_htmx(self, node: NonHTMXNode) -> Any: pass
    
    # Assets
    @abstractmethod
    def visit_css(self, node: CSSNode) -> Any: pass
    
    @abstractmethod
    def visit_js(self, node: JSNode) -> Any: pass
    
    @abstractmethod
    def visit_vite(self, node: ViteNode) -> Any: pass
    
    # Data
    @abstractmethod
    def visit_let(self, node: LetNode) -> Any: pass
    
    @abstractmethod
    def visit_dump(self, node: DumpNode) -> Any: pass
    
    @abstractmethod
    def visit_span(self, node: SpanNode) -> Any: pass
    
    @abstractmethod
    def visit_messages(self, node: MessagesNode) -> Any: pass
    
    @abstractmethod
    def visit_flash(self, node: FlashNode) -> Any: pass
    
    @abstractmethod
    def visit_status(self, node: StatusNode) -> Any: pass
    
    # Special
    @abstractmethod
    def visit_include(self, node: IncludeNode) -> Any: pass
    
    @abstractmethod
    def visit_fragment(self, node: FragmentNode) -> Any: pass
    
    # Meta
    @abstractmethod
    def visit_method(self, node: MethodNode) -> Any: pass
    
    @abstractmethod
    def visit_old(self, node: OldNode) -> Any: pass
    
    @abstractmethod
    def visit_json(self, node: JSONNode) -> Any: pass
    
    # Expressions
    @abstractmethod
    def visit_binary_op(self, node: BinaryOpNode) -> Any: pass
    
    @abstractmethod
    def visit_unary_op(self, node: UnaryOpNode) -> Any: pass
    
    @abstractmethod
    def visit_filter(self, node: FilterNode) -> Any: pass
    
    @abstractmethod
    def visit_test(self, node: TestNode) -> Any: pass
    
    @abstractmethod
    def visit_call(self, node: CallNode) -> Any: pass
    
    # References & Literals
    @abstractmethod
    def visit_variable(self, node: VariableNode) -> Any: pass
    
    @abstractmethod
    def visit_literal(self, node: LiteralNode) -> Any: pass
    
    @abstractmethod
    def visit_property_access(self, node: PropertyAccessNode) -> Any: pass
    
    @abstractmethod
    def visit_array_access(self, node: ArrayAccessNode) -> Any: pass
    
    # Collections
    @abstractmethod
    def visit_list(self, node: ListNode) -> Any: pass
    
    @abstractmethod
    def visit_dict(self, node: DictNode) -> Any: pass


# ============================================================================
# DEFAULT VISITOR IMPLEMENTATION
# ============================================================================

class DefaultASTVisitor(ASTVisitor):
    """
    Default visitor implementation with no-op visits for all node types.
    
    Useful for:
      - Base class for custom visitors
      - Traversal-only operations (visiting all nodes)
      - Debugging AST traversal
    
    Subclass and override specific visit_* methods to implement custom behavior.
    """
    
    def generic_visit(self, node: ASTNode) -> Any:
        """Default: recursively visit all children."""
        for child in node.children:
            if child:
                child.accept(self)
        return None
    
    # Collection
    def visit_template(self, node: TemplateNode) -> Any:
        for stmt in node.statements:
            stmt.accept(self)
        return None
    
    def visit_text(self, node: TextNode) -> Any:
        return None
    
    # Control Flow
    def visit_if(self, node: IfNode) -> Any:
        return self.generic_visit(node)
    
    def visit_unless(self, node: UnlessNode) -> Any:
        return self.generic_visit(node)
    
    def visit_for(self, node: ForNode) -> Any:
        return self.generic_visit(node)
    
    def visit_foreach(self, node: ForeachNode) -> Any:
        return self.generic_visit(node)
    
    def visit_switch(self, node: SwitchNode) -> Any:
        return self.generic_visit(node)
    
    def visit_case(self, node: CaseNode) -> Any:
        return self.generic_visit(node)
    
    def visit_break(self, node: BreakNode) -> Any:
        return None
    
    def visit_continue(self, node: ContinueNode) -> Any:
        return None
    
    # Components
    def visit_component(self, node: ComponentNode) -> Any:
        return self.generic_visit(node)
    
    def visit_slot(self, node: SlotNode) -> Any:
        return self.generic_visit(node)
    
    def visit_render_field(self, node: RenderFieldNode) -> Any:
        return self.generic_visit(node)
    
    def visit_props(self, node: PropsNode) -> Any:
        return self.generic_visit(node)
    
    # Inheritance
    def visit_extends(self, node: ExtendsNode) -> Any:
        return None
    
    def visit_block(self, node: BlockNode) -> Any:
        return self.generic_visit(node)
    
    def visit_yield(self, node: YieldNode) -> Any:
        return self.generic_visit(node)
    
    def visit_section(self, node: SectionNode) -> Any:
        return self.generic_visit(node)
    
    def visit_push(self, node: PushNode) -> Any:
        return self.generic_visit(node)
    
    def visit_super(self, node: SuperNode) -> Any:
        return None
    
    # Forms
    def visit_csrf_token(self, node: CSRFTokenNode) -> Any:
        return None
    
    def visit_checked(self, node: CheckedNode) -> Any:
        return self.generic_visit(node)
    
    def visit_selected(self, node: SelectedNode) -> Any:
        return self.generic_visit(node)
    
    def visit_disabled(self, node: DisabledNode) -> Any:
        return None
    
    def visit_readonly(self, node: ReadonlyNode) -> Any:
        return None
    
    def visit_error(self, node: ErrorNode) -> Any:
        return None
    
    # Routing
    def visit_url(self, node: UrlNode) -> Any:
        return self.generic_visit(node)
    
    def visit_active_link(self, node: ActiveLinkNode) -> Any:
        return self.generic_visit(node)
    
    def visit_route(self, node: RouteNode) -> Any:
        return None
    
    # Auth
    def visit_auth(self, node: AuthNode) -> Any:
        return self.generic_visit(node)
    
    def visit_guest(self, node: GuestNode) -> Any:
        return self.generic_visit(node)
    
    def visit_htmx(self, node: HTMXNode) -> Any:
        return self.generic_visit(node)
    
    def visit_non_htmx(self, node: NonHTMXNode) -> Any:
        return self.generic_visit(node)
    
    # Assets
    def visit_css(self, node: CSSNode) -> Any:
        return None
    
    def visit_js(self, node: JSNode) -> Any:
        return None
    
    def visit_vite(self, node: ViteNode) -> Any:
        return None
    
    # Data
    def visit_let(self, node: LetNode) -> Any:
        return self.generic_visit(node)
    
    def visit_dump(self, node: DumpNode) -> Any:
        return self.generic_visit(node)
    
    def visit_span(self, node: SpanNode) -> Any:
        return self.generic_visit(node)
    
    def visit_messages(self, node: MessagesNode) -> Any:
        return self.generic_visit(node)
    
    def visit_flash(self, node: FlashNode) -> Any:
        return None
    
    def visit_status(self, node: StatusNode) -> Any:
        return self.generic_visit(node)
    
    # Special
    def visit_include(self, node: IncludeNode) -> Any:
        return None
    
    def visit_fragment(self, node: FragmentNode) -> Any:
        return self.generic_visit(node)
    
    # Meta
    def visit_method(self, node: MethodNode) -> Any:
        return None
    
    def visit_old(self, node: OldNode) -> Any:
        return None
    
    def visit_json(self, node: JSONNode) -> Any:
        return self.generic_visit(node)
    
    # Expressions
    def visit_binary_op(self, node: BinaryOpNode) -> Any:
        return self.generic_visit(node)
    
    def visit_unary_op(self, node: UnaryOpNode) -> Any:
        return self.generic_visit(node)
    
    def visit_filter(self, node: FilterNode) -> Any:
        return self.generic_visit(node)
    
    def visit_test(self, node: TestNode) -> Any:
        return self.generic_visit(node)
    
    def visit_call(self, node: CallNode) -> Any:
        return self.generic_visit(node)
    
    # References & Literals
    def visit_variable(self, node: VariableNode) -> Any:
        return None
    
    def visit_literal(self, node: LiteralNode) -> Any:
        return None
    
    def visit_property_access(self, node: PropertyAccessNode) -> Any:
        return self.generic_visit(node)
    
    def visit_array_access(self, node: ArrayAccessNode) -> Any:
        return self.generic_visit(node)
    
    # Collections
    def visit_list(self, node: ListNode) -> Any:
        return self.generic_visit(node)
    
    def visit_dict(self, node: DictNode) -> Any:
        return self.generic_visit(node)


