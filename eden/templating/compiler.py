
from __future__ import annotations
import json as _json
import logging
from typing import Any, List, Optional, Type
from .parser import Node, TextNode, DirectiveNode

logger = logging.getLogger("eden.templating")

class TemplateCompiler:
    def compile(self, nodes: List[Node]) -> str:
        parts = []
        for node in nodes:
            parts.append(self.visit(node))
        return "".join(parts)

    def visit(self, node: Node) -> str:
        if isinstance(node, TextNode): return node.content
        if isinstance(node, DirectiveNode): return self.visit_directive(node)
        return ""

    def visit_directive(self, node: DirectiveNode) -> str:
        name = node.name
        expr = node.expression
        if expr and expr.startswith('(') and expr.endswith(')'):
            expr = expr[1:-1]
        
        from eden.template_directives import DIRECTIVE_REGISTRY
        handler = DIRECTIVE_REGISTRY.get(name)
        if handler:
            return handler(self, node, expr)
            
        # HARDENING: If unknown, revert to literal text instead of a comment
        # This makes the engine "unbreakable" when encountering unknown @ symbols
        # But WARN the developer so typos don't go unnoticed
        logger.warning(
            f"Unknown template directive: @{name} (line {node.line}, col {node.column}). "
            f"If this is intentional, use @@{name} to escape."
        )
        return f"@{name}" + (f"({expr})" if expr else "")

    def reconstruct(self, nodes: List[Node]) -> str:
        """Reconstruct the original source from nodes (best effort)."""
        res = []
        for node in nodes:
            if isinstance(node, TextNode):
                res.append(node.content)
            elif isinstance(node, DirectiveNode):
                res.append(f"@{node.name}")
                if node.expression:
                    res.append(node.expression) # Includes parentheses
                if node.body:
                    res.append(" {")
                    res.append(self.reconstruct(node.body))
                    res.append("}")
                for orelse in node.orelse:
                    res.append(self.reconstruct([orelse]))
        return "".join(res)

    def handle_props(self, props_val: str) -> str:
        """
        Processes @props directive to set default variable values.
        Supports both list ['a', 'b'] and dict ['a' => 'default'] syntax.
        """
        try:
            props_val = props_val.strip()
            # Remove outer brackets if present
            if (props_val.startswith('[') and props_val.endswith(']')) or \
               (props_val.startswith('{') and props_val.endswith('}')):
                props_val = props_val[1:-1].strip()
            
            if not props_val:
                return ""

            res_lines = []
            # Split by comma but respect nested structures (simplified for now)
            # A more robust regex might be needed for complex nested defaults
            parts = []
            current = []
            depth = 0
            for char in props_val:
                if char == ',' and depth == 0:
                    parts.append("".join(current).strip())
                    current = []
                else:
                    if char in '[({': depth += 1
                    elif char in '])}': depth -= 1
                    current.append(char)
            if current:
                parts.append("".join(current).strip())

            for part in parts:
                if '=>' in part:
                    k, v = part.split('=>', 1)
                    k = k.strip().strip("'\"")
                    v = v.strip().replace('$', '')
                    res_lines.append(f'{{% set {k} = {k} if {k} is defined else {v} %}}')
                elif ':' in part:
                    k, v = part.split(':', 1)
                    k = k.strip().strip("'\"")
                    v = v.strip().replace('$', '')
                    res_lines.append(f'{{% set {k} = {k} if {k} is defined else {v} %}}')
                else:
                    k = part.strip().strip("'\"")
                    res_lines.append(f'{{% set {k} = {k} if {k} is defined else None %}}')
            
            return "".join(res_lines)
        except Exception as e:
            return f"<!-- @props error: {str(e)} -->"

    def handle_class(self, val: str) -> str:
        try:
            content = val.strip(' []{}')
            if not content: return 'class=""'
            parts = []
            for part in content.split(','):
                part = part.strip()
                if '=>' in part:
                    k, v = part.split('=>', 1)
                    k = k.strip().strip('"\'')
                    v = v.strip().replace('$', '')
                    parts.append(f'("{k}" if {v} else "")')
                elif ':' in part:
                    k, v = part.split(':', 1)
                    k = k.strip().strip('"\'')
                    v = v.strip().replace('$', '')
                    parts.append(f'("{k}" if {v} else "")')
                else:
                    k = part.strip().strip('"\'')
                    parts.append(f'"{k}"')
            res = " + \" \" + ".join(parts)
            return f'class="{{{{ ({res}).strip() }}}}"'
        except Exception as e: return f'class="<!-- @class error: {str(e)} -->"'

    def handle_url(self, expr: str) -> str:
        name_part, alias = expr.split(' as ') if ' as ' in expr else (expr, None)
        parts = [p.strip() for p in name_part.strip().split(',', 1)]
        raw_name = parts[0].strip('"\'')
        kwargs = parts[1] if len(parts) > 1 else ""
        normalized_name = raw_name
        args = f'"component:dispatch", action_slug="{raw_name.split(":")[1]}"' + (f", {kwargs}" if kwargs else "") if raw_name.startswith("component:") else f'"{normalized_name}"' + (f", {kwargs}" if kwargs else "")
        return f'{{% set {alias.strip()} = url_for({args}) %}}' if alias else f'{{{{ url_for({args}) }}}}'
