from __future__ import annotations

import json as _json
import logging
from typing import Any, List, Optional, Type

from .parser import Node, TextNode, DirectiveNode
from eden.template_directives import DIRECTIVE_REGISTRY

logger = logging.getLogger("eden.templating")


class TemplateCompiler:
    def compile(self, nodes: List[Node]) -> str:
        # Pre-process: Lift headless directives in extended templates
        nodes = self._lift_nodes(nodes)
        
        parts = []
        for node in nodes:
            parts.append(self.visit(node))
        return "".join(parts)

    def _lift_nodes(self, nodes: List[Node]) -> List[Node]:
        """
        Lifts top-level directives (like @push, @set) into the first available @section 
        in a template that uses @extends. Without this, Jinja2 ignores them.
        """
        from .parser import DirectiveNode, TextNode
        
        # Check if this template explicitly extends another
        has_extends = any(isinstance(n, DirectiveNode) and n.name == "extends" for n in nodes)
        if not has_extends:
            return nodes

        # Find all available blocks/sections in this template
        sections = [n for n in nodes if isinstance(n, DirectiveNode) and n.name in ("section", "block")]
        if not sections:
            # If there are no sections to lift into, we can't do much.
            # The template is essentially broken for Jinja2 anyway.
            return nodes

        # Identify nodes to lift: those that aren't extends or section, 
        # and aren't just whitespace TextNodes.
        liftable = []
        keep = []
        for node in nodes:
            is_extends = isinstance(node, DirectiveNode) and node.name == "extends"
            is_section = isinstance(node, DirectiveNode) and node.name in ("section", "block")
            
            if is_extends or is_section:
                keep.append(node)
                continue
            
            # Substantive content? (directives or non-whitespace text)
            is_substantive = True
            if isinstance(node, TextNode):
                if not node.content.strip():
                    is_substantive = False
            
            if is_substantive:
                liftable.append(node)
            else:
                # Keep whitespace in its original relative position
                keep.append(node)

        if not liftable:
            return nodes

        # Inject liftable nodes into the start of the first section's body.
        # This ensures they are executed by Jinja2 during the block render cycle.
        first_section = sections[0]
        if first_section.body is None:
            first_section.body = []
        
        first_section.body = liftable + first_section.body
        
        return keep

    def visit(self, node: Node) -> str:
        if isinstance(node, TextNode):
            return node.content
        if isinstance(node, DirectiveNode):
            return self.visit_directive(node)
        return ""

    def _validate_directive_args(self, name: str, expr: str | None, node: DirectiveNode) -> str | None:
        """
        Validate directive arguments before handler dispatch.

        Returns None if valid, or an HTML comment string with the error
        message if validation fails. The caller should return this string
        instead of invoking the handler.

        Validation rules:
        - @for/@foreach: expression must contain the 'in' keyword
        - @if/@unless/@elif/@elseif/@else_if: expression must not be empty
        - @switch/@fragment: expression must not be empty
        - @else/@empty: only valid after conditionals or loops
        - @break/@continue: only valid inside loops
        """
        # Directives that require a non-empty expression with 'in' keyword
        if name in ("for", "foreach"):
            if not expr or " in " not in expr:
                msg = (
                    f"@{name} directive requires 'variable in collection' syntax "
                    f"(e.g., @{name}(item in items)). "
                    f"Got: @{name}({expr or ''})"
                )
                logger.warning(
                    f"Directive validation failed at line {node.line}: {msg}"
                )
                return f"<!-- EDEN TEMPLATE WARNING: {msg} -->"

        # Directives that require a non-empty expression
        if name in ("if", "unless", "elif", "elseif", "else_if"):
            if not expr or not expr.strip():
                msg = (
                    f"@{name} directive requires a condition expression "
                    f"(e.g., @{name}(user.is_admin)). Got empty expression."
                )
                logger.warning(
                    f"Directive validation failed at line {node.line}: {msg}"
                )
                return f"<!-- EDEN TEMPLATE WARNING: {msg} -->"

        if name in ("switch", "fragment"):
            if not expr or not expr.strip():
                msg = (
                    f"@{name} directive requires an argument "
                    f"(e.g., @{name}(value)). Got empty expression."
                )
                logger.warning(
                    f"Directive validation failed at line {node.line}: {msg}"
                )
                return f"<!-- EDEN TEMPLATE WARNING: {msg} -->"

        # FIXED: @else/@empty only valid after conditionals/loops
        # Note: This is a basic check. Full validation would require tracking block stack
        if name in ("else", "empty"):
            # Log warning but don't block - parser should handle context tracking
            if not hasattr(node, '_parent_type'):
                logger.debug(
                    f"@{name} at line {node.line} - verify it follows @if/@for/@while"
                )

        # FIXED: @break/@continue only valid inside loops
        if name in ("break", "continue"):
            if not hasattr(node, '_in_loop') or not node._in_loop:
                logger.debug(
                    f"@{name} at line {node.line} - should only appear inside loops"
                )

        return None  # Validation passed

    def visit_directive(self, node: DirectiveNode) -> str:
        name = node.name
        expr = node.expression
        if expr and expr.startswith("(") and expr.endswith(")"):
            expr = expr[1:-1]

        # Phase 3: Validate directive arguments before dispatch
        validation_error = self._validate_directive_args(name, expr, node)
        if validation_error is not None:
            return validation_error

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
                    res.append(node.expression)  # Includes parentheses
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
        import re
        try:
            props_val = props_val.strip()
            # Remove outer brackets if present
            if (props_val.startswith("[") and props_val.endswith("]")) or (
                props_val.startswith("{") and props_val.endswith("}")
            ):
                props_val = props_val[1:-1].strip()

            if not props_val:
                return ""

            res_lines = []
            # Split by comma but respect nested structures (simplified for now)
            parts = []
            current = []
            depth = 0
            for char in props_val:
                if char == "," and depth == 0:
                    parts.append("".join(current).strip())
                    current = []
                else:
                    if char in "[({":
                        depth += 1
                    elif char in "])}":
                        depth -= 1
                    current.append(char)
            if current:
                parts.append("".join(current).strip())

            for part in parts:
                if "=>" in part:
                    k, v = part.split("=>", 1)
                elif ":" in part:
                    k, v = part.split(":", 1)
                else:
                    k = part
                    v = "None"
                    
                k = k.strip().strip("\"'")
                v = v.strip().replace("$", "")
                
                # VALIDATION: Prevent SSTI / RCE by ensuring k is a valid Python identifier
                if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", k):
                    res_lines.append(f"<!-- @props error: Invalid property name '{k}' -->")
                    continue
                    
                res_lines.append(f"{{% set {k} = {k} if {k} is defined else {v} %}}")

            return "".join(res_lines)
        except Exception as e:
            from markupsafe import escape
            error_msg = escape(str(e))
            return f"<!-- @props error: {error_msg} -->"

    def handle_class(self, val: str) -> str:
        import re
        try:
            content = val.strip(" []{}")
            if not content:
                return 'class=""'
            parts = []
            for part in content.split(","):
                part = part.strip()
                if "=>" in part:
                    k, v = part.split("=>", 1)
                elif ":" in part:
                    k, v = part.split(":", 1)
                else:
                    k = part
                    v = None
                    
                k = k.strip().strip("\"'")
                
                # VALIDATION: Prevent SSTI / RCE by ensuring k is a valid CSS class name
                if not re.match(r"^[a-zA-Z0-9_\-]+$", k):
                    return f'class="<!-- @class error: Invalid class name \'{k}\' -->"'
                    
                if v is not None:
                    v = v.strip().replace("$", "")
                    parts.append(f'("{k}" if {v} else "")')
                else:
                    parts.append(f'"{k}"')
            res = ' + " " + '.join(parts)
            return f'class="{{{{ ({res}).strip() }}}}"'
        except Exception as e:
            # FIXED: Escape error message to prevent XSS in HTML comment
            from markupsafe import escape
            error_msg = escape(str(e))
            return f'class="<!-- @class error: {error_msg} -->"'

    def handle_url(self, expr: str) -> str:
        try:
            name_part, alias = expr.split(" as ") if " as " in expr else (expr, None)
            parts = [p.strip() for p in name_part.strip().split(",", 1)]
            raw_name = parts[0].strip("\"'")
            kwargs = parts[1] if len(parts) > 1 else ""
            normalized_name = raw_name
            args = (
                f'"component:dispatch", action_slug="{raw_name.split(":")[1]}"'
                + (f", {kwargs}" if kwargs else "")
                if raw_name.startswith("component:")
                else f'"{normalized_name}"' + (f", {kwargs}" if kwargs else "")
            )
            return (
                f"{{% set {alias.strip()} = url_for({args}) %}}"
                if alias
                else f"{{{{ url_for({args}) }}}}"
            )
        except Exception as e:
            return f"<!-- @url error: {str(e)} -->"
