
from __future__ import annotations
import json as _json
from typing import Any, List, Optional, Type
from .parser import Node, TextNode, DirectiveNode

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
            
        return f"<!-- Unknown @{name} -->"

    def handle_props(self, props_val: str) -> str:
        try:
            import ast
            props_val = props_val.strip()
            if '=>' in props_val:
                items = []
                content = props_val.strip(' []{}')
                for part in content.split(','):
                    if '=>' in part:
                        k, v = part.split('=>')
                        items.append(f"{k.strip()}: {v.strip()}")
                    else:
                        items.append(f"{part.strip()}: None")
                props_val = "{" + ", ".join(items) + "}"
            props_dict = ast.literal_eval(props_val)
            if isinstance(props_dict, list): props_dict = {k: None for k in props_dict}
            res_lines = []
            for k, v in props_dict.items():
                jinja_val = _json.dumps(v)
                res_lines.append(f'{{% set {k} = {k} if {k} is defined else {jinja_val} %}}')
            return "".join(res_lines)
        except Exception as e: return f"<!-- @props error: {str(e)} -->"

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
