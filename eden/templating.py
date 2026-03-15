from __future__ import annotations
import datetime
import json as _json
import re
from typing import Any

from jinja2 import Environment
from jinja2.ext import Extension
from markupsafe import Markup
from starlette.background import BackgroundTask
from starlette.responses import HTMLResponse
from starlette.templating import Jinja2Templates as StarletteJinja2Templates
from eden.responses import HtmlResponse
# Default styles for the @dump directive
DEFAULT_DUMP_STYLE = (
    "eden-dump p-4 bg-gray-950 text-gray-300 rounded-lg overflow-auto "
    "text-xs font-mono border border-gray-800 my-4"
)

from enum import Enum, auto
from dataclasses import dataclass, field

class TokenType(Enum):
    TEXT = auto()
    DIRECTIVE = auto()      # @name
    EXPRESSION = auto()     # (args)
    BLOCK_OPEN = auto()     # {
    BLOCK_CLOSE = auto()    # }
    ESCAPED_AT = auto()     # @@
    COMMENT = auto()        # <!-- ... --> or {# ... #}
    JINJA_TAG = auto()      # {{ ... }} or {% ... %}
    STRING = auto()         # "..." or '...' or `...`
    EOF = auto()

@dataclass
class Token:
    type: TokenType
    value: str
    line: int
    column: int

class Node:
    pass

@dataclass
class TextNode(Node):
    content: str

@dataclass
class DirectiveNode(Node):
    name: str
    expression: str | None = None
    body: list[Node] | None = None
    line: int = 0
    orelse: list[Node] = field(default_factory=list)

class TemplateLexer:
    """
    State-aware scanner for Eden templates.
    Ensures @directives are NOT identified inside strings, comments, or script/style blocks.
    """
    def __init__(self, source: str):
        self.source = source
        self.pos = 0
        self.line = 1
        self.column = 1
        self.tokens = []

    def peek(self, n=1):
        return self.source[self.pos : self.pos + n]

    def advance(self, n=1):
        res = self.source[self.pos : self.pos + n]
        for char in res:
            if char == '\n':
                self.line += 1
                self.column = 1
            else:
                self.column += 1
        self.pos += n
        return res

    def tokenize(self) -> list[Token]:
        while self.pos < len(self.source):
            char = self.peek()
            
            # 1. Escaped @
            if char == '@' and self.peek(2) == '@@':
                self.tokens.append(Token(TokenType.ESCAPED_AT, self.advance(2), self.line, self.column))
                continue

            # 2. Comments & Script/Style Blocks (Special Text)
            if char == '<':
                if self.peek(4) == '<!--':
                    content = self.read_until('-->', consume_enclosure=True)
                    self.tokens.append(Token(TokenType.COMMENT, content, self.line, self.column))
                    continue
                if self.peek(7).lower() == '<script':
                    self.tokens.append(Token(TokenType.TEXT, self.read_until_tag('script'), self.line, self.column))
                    continue
                if self.peek(6).lower() == '<style':
                    self.tokens.append(Token(TokenType.TEXT, self.read_until_tag('style'), self.line, self.column))
                    continue

            # 3. Jinja2 Tags
            if char == '{':
                if self.peek(2) in ('{{', '{%', '{#'):
                    closer = '}}' if self.peek(2) == '{{' else '%}' if self.peek(2) == '{%' else '#}'
                    content = self.read_until(closer, consume_enclosure=True)
                    self.tokens.append(Token(TokenType.JINJA_TAG, content, self.line, self.column))
                    continue

            # 4. Directives
            if char == '@':
                # Avoid matching emails: must be at start or preceded by non-alphanumeric
                can_be_directive = True
                if self.pos > 0:
                    prev_char = self.source[self.pos - 1]
                    if prev_char.isalnum() or prev_char == '_':
                        can_be_directive = False
                
                if can_be_directive:
                    # Check if it's a valid directive name prefix
                    m = re.match(r'@([a-zA-Z_]\w*)', self.source[self.pos:])
                    if m:
                        name = m.group(1)
                        full_match = m.group(0)
                        
                        # Support "@else if" syntax by normalizing to "elif"
                        if name == "else":
                            remaining = self.source[self.pos + len(full_match):]
                            m_elif = re.match(r'\s+if\b', remaining)
                            if m_elif:
                                name = "elif"
                                full_match += m_elif.group(0)

                        token_line, token_col = self.line, self.column
                        self.advance(len(full_match))
                        self.tokens.append(Token(TokenType.DIRECTIVE, name, token_line, token_col))
                        
                        # Optional arguments: @name(...)
                        # Skip whitespace to find (
                        saved_pos_expr = self.pos
                        saved_line_expr, saved_col_expr = self.line, self.column
                        ws_expr = ""
                        while self.pos < len(self.source) and self.source[self.pos].isspace():
                            ws_expr += self.advance()
                        
                        if self.peek() == '(':
                            expr_line, expr_col = self.line, self.column
                            expr = self.read_balanced('(', ')')
                            self.tokens.append(Token(TokenType.EXPRESSION, expr, expr_line, expr_col))
                        elif name in ("let", "php", "json", "dump", "css", "js", "vite", "method", "csrf"):
                            # Directives that might take the rest of the line as expression
                            # Consumed above ws_expr, but if not ( it might be a raw expr
                            # Backtrack to after name
                            self.pos = saved_pos_expr
                            self.line = saved_line_expr
                            self.column = saved_col_expr
                            
                            # Read until end of line or {
                            raw_expr = self.read_until(lambda c: c == '\n' or c == '{').strip()
                            if raw_expr:
                                self.tokens.append(Token(TokenType.EXPRESSION, raw_expr, self.line, self.column))
                        else:
                            # Backtrack
                            self.pos = saved_pos_expr
                            self.line = saved_line_expr
                            self.column = saved_col_expr

                        # Optional block open: {
                        # Skip whitespace to find {
                        saved_pos = self.pos
                        saved_line, saved_col = self.line, self.column
                        ws = ""
                        while self.pos < len(self.source) and self.source[self.pos].isspace():
                            ws += self.advance()
                        
                        if self.peek() == '{':
                            # It's a block!
                            if ws: self.tokens.append(Token(TokenType.TEXT, ws, saved_line, saved_col))
                            self.tokens.append(Token(TokenType.BLOCK_OPEN, self.advance(), self.line, self.column))
                        else:
                            # Not a block, backtrack WS move
                            self.pos = saved_pos
                            self.line = saved_line
                            self.column = saved_col
                            self.pos = saved_pos
                            self.line = saved_line
                            self.column = saved_col
                        continue

            # 5. Braces (for blocks)
            if char == '}':
                self.tokens.append(Token(TokenType.BLOCK_CLOSE, self.advance(), self.line, self.column))
                continue
            
            if char == '{':
                self.tokens.append(Token(TokenType.BLOCK_OPEN, self.advance(), self.line, self.column))
                continue

            # 6. Fallback: Generic Text
            text = self.read_until(lambda c: c in ('@', '{', '}', '<'), False)
            if not text and self.pos < len(self.source):
                text = self.advance()
            if text:
                self.tokens.append(Token(TokenType.TEXT, text, self.line, self.column))

        self.tokens.append(Token(TokenType.EOF, '', self.line, self.column))
        return self.tokens

    def read_until(self, closer: str | Any, consume_enclosure: bool = False) -> str:
        start = self.pos
        if isinstance(closer, str):
            idx = self.source.find(closer, self.pos)
            if idx == -1:
                res = self.source[self.pos:]
                self.advance(len(self.source) - self.pos)
                return res
            target = idx + (len(closer) if consume_enclosure else 0)
            res = self.source[start:target]
            self.advance(target - self.pos)
            return res
        else:
            # Predicate version
            while self.pos < len(self.source) and not closer(self.source[self.pos]):
                self.advance()
            return self.source[start : self.pos]

    def read_until_tag(self, tag_name: str) -> str:
        closer = f"</{tag_name}>"
        idx = self.source.lower().find(closer.lower(), self.pos)
        if idx == -1:
            return self.advance(len(self.source) - self.pos)
        
        target = idx + len(closer)
        return self.advance(target - self.pos)

    def read_balanced(self, open_str: str, close_str: str) -> str:
        start_pos = self.pos
        self.advance(len(open_str))
        depth = 1
        while self.pos < len(self.source):
            char = self.source[self.pos]
            if char in ("'", '"', '`'):
                # Skip strings
                quote = self.advance()
                while self.pos < len(self.source):
                    if self.source[self.pos] == quote:
                        if self.source[self.pos - 1] != '\\':
                            self.advance()
                            break
                    self.advance()
                continue
                
            if self.source.startswith(open_str, self.pos):
                depth += 1
                self.advance(len(open_str))
            elif self.source.startswith(close_str, self.pos):
                depth -= 1
                self.advance(len(close_str))
                if depth == 0:
                    return self.source[start_pos : self.pos]
            else:
                self.advance()
        return self.source[start_pos:]

class TemplateParser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0

    def peek(self):
        return self.tokens[self.pos]

    def advance(self):
        res = self.tokens[self.pos]
        self.pos += 1
        return res

    def parse(self) -> list[Node]:
        nodes = []
        while self.peek().type != TokenType.EOF:
            node = self.parse_node()
            if node:
                nodes.append(node)
        
        # Group if/elif/else chains
        return self._group_conditionals(nodes)

    def _group_conditionals(self, nodes: list[Node]) -> list[Node]:
        new_nodes = []
        i = 0
        while i < len(nodes):
            node = nodes[i]
            if isinstance(node, DirectiveNode) and node.name in ("if", "unless"):
                chain = node
                curr = chain
                while i + 1 < len(nodes):
                    next_idx = i + 1
                    maybe_ws = nodes[next_idx]
                    if isinstance(maybe_ws, TextNode) and maybe_ws.content.isspace():
                        if next_idx + 1 < len(nodes):
                            next_node = nodes[next_idx + 1]
                            if isinstance(next_node, DirectiveNode) and next_node.name in ("else", "elif", "elseif"):
                                curr.orelse.extend([maybe_ws, next_node])
                                curr = next_node
                                i = next_idx + 1
                                continue
                    elif isinstance(maybe_ws, DirectiveNode) and maybe_ws.name in ("else", "elif", "elseif"):
                        curr.orelse.append(maybe_ws)
                        curr = maybe_ws
                        i = next_idx
                        continue
                    break
                new_nodes.append(chain)
            else:
                new_nodes.append(node)
            i += 1
        return new_nodes

    def parse_node(self) -> Node | None:
        token = self.peek()
        
        if token.type == TokenType.DIRECTIVE:
            directive_token = self.advance()
            expression = None
            if self.peek().type == TokenType.EXPRESSION:
                expression = self.advance().value
            
            block_directives = (
                "if", "unless", "else", "elif", "elseif", "for", "foreach", "switch", "case", "default",
                "auth", "guest", "htmx", "non_htmx", "fragment", "push", "verbatim",
                "section", "block", "slot", "component", "error", "messages",
                "even", "odd", "first", "last"
            )
            
            if directive_token.value in block_directives:
                saved_pos = self.pos
                ws_nodes = []
                while self.peek().type == TokenType.TEXT and self.peek().value.isspace():
                    ws_nodes.append(TextNode(content=self.advance().value))
                
                if self.peek().type == TokenType.BLOCK_OPEN:
                    self.advance() # consume {
                    body = []
                    while self.peek().type != TokenType.BLOCK_CLOSE and self.peek().type != TokenType.EOF:
                        n = self.parse_node()
                        if n: body.append(n)
                    
                    if self.peek().type == TokenType.BLOCK_CLOSE:
                        self.advance() # consume }
                    
                    # Group conditionals recursively within the body
                    grouped_body = self._group_conditionals(body)
                    
                    return DirectiveNode(
                        name=directive_token.value,
                        expression=expression,
                        body=grouped_body,
                        line=directive_token.line
                    )
                else:
                    self.pos = saved_pos
            
            return DirectiveNode(
                name=directive_token.value,
                expression=expression,
                line=directive_token.line
            )
            
        elif token.type == TokenType.BLOCK_CLOSE:
            return TextNode(content=self.advance().value)
        else:
            t = self.advance()
            content = t.value
            if t.type == TokenType.ESCAPED_AT:
                content = '@'
            return TextNode(content=content)

class TemplateCompiler:
    def compile(self, nodes: list[Node]) -> str:
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
        
        if name == "csrf": return '<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">'
        if name == "eden_head": return '{{ eden_head() }}'
        if name == "eden_scripts": return '{{ eden_scripts() }}'
        if name == "method": 
            val = expr.strip("'\"") if expr else "POST"
            return f'<input type="hidden" name="_method" value="{val}">'
        if name == "yield": 
            val = expr.strip("'\"") if expr else "content"
            return f'{{% block {val} %}}{{% endblock %}}'
        if name == "stack": return f'{{{{ eden_stack({expr}) }}}}'
        if name == "super": return '{{ super() }}'
        if name == "extends": return f'{{% extends {expr} %}}'
        if name == "include": return f'{{% include {expr} %}}'
        if name == "css": return f'<link rel="stylesheet" href={expr}>'
        if name == "js": return f'<script src={expr}></script>'
        if name == "vite": return f'{{{{ vite({expr}) }}}}'
        if name == "old":
            parts = [p.strip() for p in (expr or "").split(',', 1)]
            name_v = parts[0]
            def_v = parts[1] if len(parts) > 1 else "None"
            return f'{{{{ old({name_v}, {def_v}) }}}}'
        if name == "span": return f'{{{{ {expr.replace("$", "")} }}}}' if expr else ""
        if name == "json": return f'{{{{ {expr} | json_encode }}}}'
        if name == "dump": 
            clean_expr = expr.replace("$", "").replace("(", "").replace(")", "").strip()
            return f'{{{{ eden_dump({expr}, "{clean_expr}") }}}} {{# eden-dump json_encode #}}'
        if name == "status": return f'{{{{ set_response_status({expr}) }}}}'
        if name in ("checked", "selected", "disabled", "readonly"): 
            return f'{{% if {expr} %}}{name}{{% endif %}}'
        if name == "let": return f"{{% set {expr} %}}"
        if name == "props": return self.handle_props(expr)
        if name == "render_field":
            parts = [p.strip() for p in (expr or "").split(',', 1)]
            field_expr = parts[0].replace('$', '')
            kwargs = parts[1] if len(parts) > 1 else ""
            return f'{{{{ {field_expr}.render_composite({kwargs}) }}}}'
        if name == "url": return self.handle_url(expr)
        if name == "active_link":
            parts = [p.strip() for p in (expr or "").split(',', 1)]
            url_v = parts[0]
            css_v = parts[1].strip('"\'')
            if url_v.startswith("'") or url_v.startswith('"'):
                url_v = f'"{url_v[1:-1].replace(":", "_")}"'
            return f'{{{{ "{css_v}" if is_active(request, {url_v}) else "" }}}}'
        if name == "class": return self.handle_class(expr)

        body_compiled = self.compile(node.body or []) if node.body is not None else ""
        if name == "if":
            res = [f"{{% if {expr} %}}" + body_compiled]
            for orelse in node.orelse:
                res.append(self.visit(orelse))
            res.append("{% endif %}")
            return "".join(res)
        
        if name == "unless":
            res = [f"{{% if not ({expr}) %}}" + body_compiled]
            for orelse in node.orelse:
                res.append(self.visit(orelse))
            res.append("{% endif %}")
            return "".join(res)
        
        if name in ("elif", "elseif"):
            res = [f"{{% elif {expr} %}}{body_compiled}"]
            for o in node.orelse: res.append(self.visit(o))
            return "".join(res)
        
        if name == "else":
            res = [f"{{% else %}}{body_compiled}"]
            for o in node.orelse: res.append(self.visit(o))
            return "".join(res)

        if name in ("for", "foreach"):
            inner = expr.replace('$', '') if expr else ""
            if ' as ' in inner:
                parts = inner.split(' as ')
                inner = f"{parts[1].strip()} in {parts[0].strip()}"
            return f"{{% for {inner} %}}" + body_compiled + "{% endfor %}"
        
        if name == "switch":
            # Process switch body to identify cases/default
            cases_compiled = []
            default_compiled = ""
            has_cases = False
            
            if node.body:
                for n in node.body:
                    if isinstance(n, DirectiveNode):
                        if n.name == "case":
                            c_expr = n.expression[1:-1] if n.expression else "None"
                            c_body = self.compile(n.body or [])
                            pfx = "{% if" if not has_cases else "{% elif"
                            cases_compiled.append(f"{pfx} __sw == {c_expr} %}}" + c_body)
                            has_cases = True
                        elif n.name == "default":
                            pfx = "{% else %}" if has_cases else "{% if True %}"
                            default_compiled = pfx + self.compile(n.body or [])
            
            res = [f"{{% with __sw = {expr} %}}"]
            res.extend(cases_compiled)
            if default_compiled:
                res.append(default_compiled)
                if not has_cases:
                    res.append("{% endif %}")
            if has_cases:
                res.append("{% endif %}")
            res.append("{% endwith %}")
            return "".join(res)

        if name == "case": return "" # Handled by switch
        if name == "default": return "" # Handled by switch
        if name == "auth":
            if expr:
                roles_list = [r.strip().strip("'\"").replace('$', '') for r in (expr or "").split(',')]
                cond = f'request.user.role == "{roles_list[0]}"' if len(roles_list) == 1 else f'request.user.role in {roles_list}'
                return f'{{% if request.user and request.user.is_authenticated and {cond} %}}{body_compiled}{{% endif %}}'
            return f'{{% if request.user and request.user.is_authenticated %}}{body_compiled}{{% endif %}}'
        if name == "guest": return f'{{% if not (request.user and request.user.is_authenticated) %}}{body_compiled}{{% endif %}}'
        if name == "htmx": return f'{{% if request.headers.get("HX-Request") == "true" %}}{body_compiled}{{% endif %}}'
        if name == "non_htmx": return f'{{% if request.headers.get("HX-Request") != "true" %}}{body_compiled}{{% endif %}}'
        if name == "fragment":
            val = expr.strip('"\'') if expr else ""
            return f'{{% block fragment_{val} %}}{body_compiled}{{% endblock %}}'
        if name == "push":
            val = expr.strip('"\'') if expr else ""
            return f'{{% set __push_content %}}{body_compiled}{{% endset %}}{{{{ eden_push("{val}", __push_content) }}}}'
        if name == "verbatim": return f'{{% raw %}}{body_compiled}{{% endraw %}}'
        if name in ("section", "block"):
            val = expr.strip('"\'') if expr else ""
            return f'{{% block {val} %}}{body_compiled}{{% endblock %}}'
        if name == "slot": return f'{{% slot {expr} %}}{body_compiled}{{% endslot %}}'
        if name == "component": return f'{{% component {expr} %}}{body_compiled}{{% endcomponent %}}'
        if name == "error": return f'{{% if errors and errors.has({expr}) %}}{{% set error = errors.first({expr}) %}}{body_compiled}{{% endif %}}'
        if name == "messages": return f'{{% for message in eden_messages() %}}{body_compiled}{{% endfor %}}'
        if name in ("even", "odd", "first", "last"): return f'{{% if loop.{name} %}}{body_compiled}{{% endif %}}'
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
        normalized_name = raw_name.replace(':', '_')
        args = f'"component:dispatch", action_slug="{raw_name.split(":")[1]}"' + (f", {kwargs}" if kwargs else "") if raw_name.startswith("component:") else f'"{normalized_name}"' + (f", {kwargs}" if kwargs else "")
        return f'{{% set {alias.strip()} = url_for({args}) %}}' if alias else f'{{{{ url_for({args}) }}}}'


class EdenDirectivesExtension(Extension):
    """
    Jinja2 extension that pre-processes Eden's modern syntax (@if, @for, etc.)
    Ensures that directives are not replaced within strings or comments.
    """
    def preprocess(self, source: str, name: str | None, filename: str | None = None) -> str:
        # 0. Tokenize
        lexer = TemplateLexer(source)
        tokens = lexer.tokenize()

        # 1. Parse into AST
        parser = TemplateParser(tokens)
        nodes = parser.parse()

        # 2. Compile AST to Jinja2
        compiler = TemplateCompiler()
        compiled = compiler.compile(nodes)

        # 4. Security: Automate target="_blank" protection
        def _enforce_noopener(m):
            tag = m.group(0)
            if 'rel=' not in tag.lower(): return tag[:-1] + ' rel="noopener noreferrer">'
            return tag
        compiled = re.sub(r'<a\s+[^>]*?target=[\'"]_blank[\'"][^>]*>', _enforce_noopener, compiled, flags=re.IGNORECASE)

        return compiled


def format_time_ago(value: datetime.datetime) -> str:
    """
    Format a datetime as a human-readable "time ago" string.
    """
    if not value:
        return ""

    now = datetime.datetime.now()
    if value.tzinfo:
        now = datetime.datetime.now(value.tzinfo)

    diff = now - value

    if diff.days > 365:
        return f"{diff.days // 365} years ago"
    if diff.days > 30:
        return f"{diff.days // 30} months ago"
    if diff.days > 0:
        return f"{diff.days} days ago"
    if diff.seconds > 3600:
        return f"{diff.seconds // 3600} hours ago"
    if diff.seconds > 60:
        return f"{diff.seconds // 60} minutes ago"
    return "just now"

def format_money(value: int | float | None, currency: str = "$") -> str:
    """
    Format a value as currency.
    """
    if value is None:
        return ""
    return f"{currency}{value:,.2f}"

def class_names(base: str, conditions: dict[str, bool]) -> str:
    """
    Angular-style class names helper.
    """
    classes = [base]
    for cls, cond in conditions.items():
        if cond:
            classes.append(cls)
    return " ".join(classes)

# ─────────────────────────────────────────────────────────────────────────────
# Widget tweaks helpers (Jinja filters)
# ─────────────────────────────────────────────────────────────────────────────

def add_class(field: Any, css_class: str) -> Any:
    if hasattr(field, "add_class"):
        return field.add_class(css_class)
    return field

def remove_class(field: Any, css_class: str) -> Any:
    if hasattr(field, "remove_class"):
        return field.remove_class(css_class)
    return field

def add_error_class(field: Any, css_class: str) -> Any:
    if hasattr(field, "add_error_class"):
        return field.add_error_class(css_class)
    return field

def attr(field: Any, name: str, value: str) -> Any:
    if hasattr(field, "attr"):
        return field.attr(name, str(value))
    return field

def set_attr(field: Any, name: str, value: str) -> Any:
    if hasattr(field, "set_attr"):
        return field.set_attr(name, str(value))
    return field

def append_attr(field: Any, name: str, value: str) -> Any:
    if hasattr(field, "append_attr"):
        return field.append_attr(name, str(value))
    return field

def remove_attr(field: Any, name: str) -> Any:
    if hasattr(field, "remove_attr"):
        return field.remove_attr(name)
    return field

def add_error_attr(field: Any, name: str, value: str) -> Any:
    if hasattr(field, "add_error_attr"):
        return field.add_error_attr(name, str(value))
    return field

def field_type(field: Any) -> str:
    if hasattr(field, "field_type"):
        return field.field_type
    return ""

def widget_type(field: Any) -> str:  # pragma: nocover – simple proxy
    if hasattr(field, "widget_type"):
        return field.widget_type
    return ""

# ─────────────────────────────────────────────────────────────────────────────
# Utility filters
# ─────────────────────────────────────────────────────────────────────────────

def truncate_filter(value: Any, length: int = 50, end: str = "…") -> str:
    """Truncate a string to *length* characters, appending *end* if truncated."""
    s = str(value)
    if len(s) <= length:
        return s
    return s[:length].rstrip() + end


def slugify_filter(value: Any) -> str:
    """Convert text to a URL-friendly slug."""
    s = str(value).lower().strip()
    s = re.sub(r'[^\w\s-]', '', s)
    return re.sub(r'[\s_]+', '-', s).strip('-')


def json_encode(value: Any) -> str:
    """Serialize value to JSON (safe for ``x-data`` attributes)."""
    return Markup(_json.dumps(value))


def default_if_none(value: Any, default: Any = "") -> Any:
    """Return *default* when *value* is ``None``."""
    return default if value is None else value


def pluralize_filter(count: Any, singular: str = "", plural: str = "s") -> str:
    """Return *singular* or *plural* suffix based on *count*."""
    try:
        n = int(count)
    except (TypeError, ValueError):
        n = 0
    return singular if n == 1 else plural


def title_case(value: Any) -> str:
    """Convert text to Title Case."""
    return str(value).title()


def mask_filter(value: Any) -> str:
    """Mask a string, showing first and last character (e.g. emails → ``u***@e.com``)."""
    s = str(value)
    if "@" in s:
        local, domain = s.split("@", 1)
        masked_local = local[0] + "***" if local else "***"
        return f"{masked_local}@{domain}"
    if len(s) <= 2:
        return "*" * len(s)
    return s[0] + "*" * (len(s) - 2) + s[-1]


def file_size_filter(value: Any) -> str:
    """Format a byte count as a human-readable file size."""
    try:
        size = float(value)
    except (TypeError, ValueError):
        return "0 B"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(size) < 1024:
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"


# ─────────────────────────────────────────────────────────────────────────────
# Fragment extraction helper
# ─────────────────────────────────────────────────────────────────────────────

def render_fragment(
    env: Environment,
    template_name: str,
    fragment_name: str,
    context: dict[str, Any],
) -> str:
    """
    Render a single named fragment from a template.

    Fragments are defined with ``@fragment("name") { ... }`` in the template.
    Internally they become Jinja2 ``{% block fragment_<name> %}`` blocks.

    Usage::

        html = render_fragment(env, "page.html", "inbox", {"messages": msgs})

    Returns the rendered HTML string for only that fragment.
    """
    block_fn_name = f"fragment_{fragment_name}"
    tmpl = env.get_template(template_name)

    if block_fn_name not in tmpl.blocks:
        raise KeyError(
            f"Fragment '{fragment_name}' not found in template '{template_name}'. "
            f"Make sure you defined @fragment(\"{fragment_name}\") {{ ... }} in the template."
        )

    # Build a real Jinja2 context and call the block render function directly.
    # template.blocks[name] is a callable that yields rendered string chunks.
    ctx = tmpl.new_context(context.copy())
    block_gen = tmpl.blocks[block_fn_name](ctx)
    return Markup("".join(block_gen))


class EdenTemplates(StarletteJinja2Templates):
    """
    Jinja2 templates with Eden logic.
    """

    def template_response(self, *args, **kwargs) -> Any:
        return self.TemplateResponse(*args, **kwargs)

    def __init__(self, directory: str | list[str], **kwargs: Any):
        if "extensions" not in kwargs:
            kwargs["extensions"] = []
        if "eden.templating.EdenDirectivesExtension" not in kwargs["extensions"]:
            kwargs["extensions"].append(EdenDirectivesExtension)
        if "eden.components.ComponentExtension" not in kwargs["extensions"]:
            kwargs["extensions"].append("eden.components.ComponentExtension")

        super().__init__(directory=directory, **kwargs)

        # ── Imports for filters / globals ────────────────────────────────────
        from eden.assets import (
            ALPINE_VERSION,
            HTMX_VERSION,
            TAILWIND_VERSION,
        )
        from eden.assets import (
            eden_head as _eden_head,
        )
        from eden.assets import (
            eden_scripts as _eden_scripts,
        )
        from eden.design import (
            eden_bg,
            eden_border,
            eden_color,
            eden_font,
            eden_shadow,
            eden_text,
        )
        from eden.htmx import hx_headers, hx_vals

        # Add default filters
        self.env.filters.update({
            # Built-in helpers
            "time_ago": format_time_ago,
            "money": format_money,
            "class_names": class_names,
            # Widget tweaks
            "add_class": add_class,
            "remove_class": remove_class,
            "add_error_class": add_error_class,
            "attr": attr,
            "set_attr": set_attr,
            "append_attr": append_attr,
            "remove_attr": remove_attr,
            "add_error_attr": add_error_attr,
            "field_type": field_type,
            "widget_type": widget_type,
            # Utility filters
            "truncate": truncate_filter,
            "slugify": slugify_filter,
            "json_encode": json_encode,
            "default_if_none": default_if_none,
            "pluralize": pluralize_filter,
            "title_case": title_case,
            "mask": mask_filter,
            "file_size": file_size_filter,
            # Design system
            "eden_color": eden_color,
            "eden_bg": eden_bg,
            "eden_text": eden_text,
            "eden_border": eden_border,
            "eden_shadow": eden_shadow,
            "eden_font": eden_font,
            # HTMX
            "hx_vals": hx_vals,
            "hx_headers": hx_headers,
        })

        # ── is_active() helper ────────────────────────────────────────────────
        def is_active(request: Any, route_name: str, **kwargs: Any) -> bool:
            """
            Return True when *request.url.path* matches the URL for *route_name*.

            Supports:
            - Exact route matching: 'dashboard'
            - Namespace routes: 'auth:login' (converted to 'auth_login')
            - Wildcard routes: 'students:*' (matches matches prefix of any resolved route starting with the namespace)
            - Prefix matching: If the current path starts with the resolved route path.

            Usage in templates::
                class="nav-link {{ 'active' if is_active(request, 'dashboard') else '' }}"
            """
            import logging
            logger = logging.getLogger("eden.templating")
            
            # Normalize path: /foo/ -> /foo
            current = request.url.path.rstrip("/") or "/"
            
            try:
                # 1. Handle wildcard routes (e.g., 'students:*' or 'admin:*')
                if route_name.endswith('*'):
                    # Convert 'students:*' -> 'students'
                    prefix = route_name[:-1].rstrip(':_').replace(':', '_')
                    
                    # Instead of guessing suffixes, we look for ANY route that starts with this prefix
                    # We'll use the first one we find to determine the base URL path.
                    from starlette.routing import Mount, Route
                    
                    base_path = None
                    
                    # We need to find the base path for this namespace
                    # A robust way is to check the app's route list
                    app = request.app
                    for route in app.routes:
                        # Check if route is a Mount or a Route with a name starting with our prefix
                        if hasattr(route, "name") and route.name and route.name.startswith(prefix):
                            try:
                                # Resolve this specific route to get its path
                                resolved = str(request.url_for(route.name, **kwargs)).rstrip("/") or "/"
                                # The base path is the common part. For a namespace, 
                                # it's usually everything up to the first param or the end of the namespace part.
                                # Heuristic: if route name is 'students_index', and path is '/students', 
                                # then '/students' is our base.
                                base_path = resolved
                                break
                            except Exception:
                                continue
                    
                    if base_path:
                        return current == base_path or current.startswith(base_path + "/")
                    
                    logger.debug(f"is_active: Could not resolve any route for wildcard '{route_name}'")
                    return False
                
                # 2. Normal (non-wildcard) route matching
                resolved = str(request.url_for(route_name, **kwargs)).rstrip("/") or "/"
                
                # Match if exact or if current is a sub-path (e.g. /tasks/1 is active for /tasks)
                return current == resolved or current.startswith(resolved + "/")
                
            except Exception as e:
                # Log the error for easier debugging
                logger.debug(f"is_active: Error resolving route '{route_name}': {e}")
                return False

        # Add default globals
        self.env.globals.update({
            "now": datetime.datetime.now,
            "is_active": is_active,
            "eden_head": _eden_head,
            "eden_scripts": _eden_scripts,
            "alpine_version": ALPINE_VERSION,
            "htmx_version": HTMX_VERSION,
            "tailwind_version": TAILWIND_VERSION,
            "old": self._old_helper,
            "vite": self._vite_helper,
            "csrf_field": self._csrf_helper,
            "eden_dump": self._dump_helper,
        })

        # ── Messaging helper ──────────────────────────────────────────────────
        def eden_messages() -> list:
            """Retrieve and clear messages from the current request."""
            from eden.context import get_request
            request = get_request()
            if request:
                return list(request.messages)
            return []

        # ── Stack helpers ───────────────────────────────────────────────────
        stacks = {}
        def eden_push(name: str, content: str):
            if name not in stacks:
                stacks[name] = []
            stacks[name].append(content)
            return ""

        def eden_stack(name: str):
            res = "\n".join(stacks.get(name, []))
            # Optional: clear after use? usually not for stacks
            return res

        self.env.globals.update({
            "eden_messages": eden_messages,
            "eden_push": eden_push,
            "eden_stack": eden_stack,
        })

    def TemplateResponse(
        self,
        name: str,
        context: dict[str, Any],
        status_code: int = 200,
        headers: dict[str, str] | None = None,
        media_type: str | None = None,
        background: BackgroundTask | None = None,
    ) -> Any:
        """
        Returns a response that renders a template.

        HTMX Auto-Fragment Detection
        ────────────────────────────
        If the request carries the ``HX-Request`` header, Eden looks for the
        ``HX-Target`` header (or an explicit ``hx-fragment`` context key) and
        automatically renders only that named fragment instead of the full page.

        Template authors don't need to write separate views — just mark regions::

            @fragment("inbox") {
              <ul>...</ul>
            }
        """
        # Ensure 'request' is in context for Starlette
        if "request" not in context:
            from eden.context import get_request
            context["request"] = get_request()

        request = context.get("request")

        # ── Context Injection (Tenant & User) ─────────────────────────────────
        if "current_tenant" not in context:
            from eden.tenancy.context import get_current_tenant
            from eden.tenancy.models import AnonymousTenant
            context["current_tenant"] = get_current_tenant() or AnonymousTenant()
            
        if "user" not in context:
            from eden.context import get_user
            context["user"] = get_user()

        # ── HTMX fragment auto-detection ──────────────────────────────────────
        if request is not None:
            # Check if this is an HTMX request
            is_htmx = getattr(request, "headers", {}).get("HX-Request") == "true"

            # Explicit override: caller can pass fragment="inbox" in context
            fragment_name = context.pop("fragment", None)

            # Or derive from HX-Target header (strip leading # if present)
            if not fragment_name and is_htmx:
                hx_target = getattr(request, "headers", {}).get("HX-Target", "")
                if hx_target:
                    fragment_name = hx_target.lstrip("#")

            if fragment_name:
                try:
                    html = render_fragment(self.env, name, fragment_name, context)
                    response_headers = dict(headers or {})
                    return HtmlResponse(
                        content=str(html),
                        status_code=status_code,
                        headers=response_headers,
                    )
                except (KeyError, ValueError):
                    # Fallback to full template if fragment not found
                    pass
        # ─────────────────────────────────────────────────────────────────────

        # ── Status Code Control ───────────────────────────────────────────────
        status_box = {"code": status_code}
        def set_response_status(code: int):
            status_box["code"] = code
            return ""
        
        context["set_response_status"] = set_response_status
        # ─────────────────────────────────────────────────────────────────────

        # Add common helpers
        context["route"] = context.get("route") or self.env.globals.get("url_for")

        response = super().TemplateResponse(
            name, context, status_code, headers, media_type, background
        )
        # Apply the status code if it was changed during rendering
        if status_box["code"] != status_code:
            response.status_code = status_box["code"]
        return response

    def _old_helper(self, name: str, default: Any = "") -> Any:
        """Helper for @old directive to retrieve previous form data."""
        from eden.context import get_request
        request = get_request()
        # 1. Check form in context (passed by app.validate)
        # We need to access the active context. Jinja globals don't have it easily.
        # But we can try to get it from a thread-local or the request itself.
        # For now, let's assume 'form' might be in the current rendering context.
        # However, TemplateResponse doesn't store the context it's currently rendering.
        # A better way is to use a contextfilter but we are in a global.
        
        # Fallback: check session if available
        if request and hasattr(request, "session"):
            old_data = request.session.get("_old_input", {})
            return old_data.get(name, default)
        
        return default

    def _vite_helper(self, inputs: str | list[str]) -> Markup:
        """Placeholder for Vite asset loading."""
        if isinstance(inputs, str):
            inputs = [inputs]
        
        tags = []
        for inp in inputs:
            if inp.endswith(".css"):
                tags.append(f'<link rel="stylesheet" href="/{inp}">')
            else:
                tags.append(f'<script type="module" src="/{inp}"></script>')
        return Markup("\n".join(tags))

    def _csrf_helper(self) -> Markup:
        """Render a hidden CSRF token input field."""
        from eden.context import get_request
        request = get_request()
        token = ""
        if request and hasattr(request, "scope"):
            # Try to get from state or session
            token = getattr(request.state, "csrf_token", "")
        return Markup(f'<input type="hidden" name="_token" value="{token}">')

    def _dump_helper(self, value: Any, label: str = "") -> Markup:
        """Premium @dump directive implementation with syntax highlighting feel."""
        import pprint
        formatted = pprint.pformat(value, indent=2)
        
        header = f'<div class="text-xs font-bold text-blue-400 mb-1">@dump: {label}</div>' if label else ""
        html = (
            f'<div class="{DEFAULT_DUMP_STYLE}">'
            f'{header}'
            f'<pre class="whitespace-pre-wrap"><code>{formatted}</code></pre>'
            f'</div>'
        )
        return Markup(html)

    def render(self, request: Any, template_name: str, context: dict[str, Any], **kwargs: Any) -> Any:
        """
        Convenience wrapper — preferred over ``TemplateResponse`` directly.

        Usage in a view::

            return templates.render(request, "inbox.html", {"messages": msgs})

        HTMX requests are handled automatically.
        """
        ctx = {"request": request, **context, **kwargs}
        return self.TemplateResponse(template_name, ctx)


def render_template(template_name: str, **context: Any) -> Any:
    """
    Render an HTML template using the current request context.

    This is a shortcut for ``request.app.render(template_name, **context)``.
    It automatically handles HTMX fragment rendering and injects standard
    context variables (request, user, tenant).

    Usage:
        return render_template("home.html", title="Home Page")
    """
    from eden.context import get_request
    request = get_request()
    if request is None:
        raise RuntimeError("render_template() must be called within a request context.")

    return request.app.render(template_name, **context)

