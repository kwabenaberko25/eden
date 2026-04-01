from __future__ import annotations
from dataclasses import dataclass, field
from .lexer import Token, TokenType

from jinja2.exceptions import TemplateSyntaxError as JinjaTemplateSyntaxError

MAX_PARSE_DEPTH = 100  # Prevent stack overflows from maliciously nested templates


class TemplateSyntaxError(JinjaTemplateSyntaxError):
    def __init__(
        self,
        message: str,
        line: int = 0,
        column: int = 0,
        name: str | None = None,
        filename: str | None = None,
        source: str | None = None,
    ):
        super().__init__(message, line, name, filename)
        self.column = column
        self.line = line
        self.source = source


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
    column: int = 0
    orelse: list[Node] = field(default_factory=list)


class TemplateParser:
    def __init__(
        self,
        tokens: list[Token],
        name: str | None = None,
        filename: str | None = None,
        source: str | None = None,
    ):
        self.tokens = tokens
        self.pos = 0
        self.name = name
        self.filename = filename
        self.source = source

    def peek(self):
        return self.tokens[self.pos]

    def advance(self):
        res = self.tokens[self.pos]
        self.pos += 1
        return res

    def parse(self) -> list[Node]:
        nodes = []
        while self.peek().type != TokenType.EOF:
            node = self.parse_node(current_depth=1)
            if node:
                nodes.append(node)

        # Group if/elif/else chains
        return self._group_conditionals(nodes)

    def _group_conditionals(self, nodes: list[Node]) -> list[Node]:
        new_nodes = []
        i = 0
        while i < len(nodes):
            node = nodes[i]
            if isinstance(node, DirectiveNode) and node.name in (
                "if",
                "unless",
                "for",
                "foreach",
                "recursive",
            ):
                chain = node
                curr = chain
                # if/unless chain can have multiple elif/elseif/else_if and one else
                # for/foreach/recursive chain can have one empty or else
                valid_followers = (
                    ("else", "elif", "elseif", "else_if")
                    if node.name in ("if", "unless")
                    else ("empty", "else")
                )

                while i + 1 < len(nodes):
                    next_idx = i + 1
                    maybe_ws = nodes[next_idx]
                    if isinstance(maybe_ws, TextNode) and maybe_ws.content.isspace():
                        if next_idx + 1 < len(nodes):
                            next_node = nodes[next_idx + 1]
                            if (
                                isinstance(next_node, DirectiveNode)
                                and next_node.name in valid_followers
                            ):
                                curr.orelse.extend([maybe_ws, next_node])
                                curr = next_node
                                i = next_idx + 1
                                # For loops, we usually only have one else/empty, but let's allow it to continue
                                if node.name in ("for", "foreach", "recursive"):
                                    i = next_idx + 1
                                    break
                                continue
                    elif isinstance(maybe_ws, DirectiveNode) and maybe_ws.name in valid_followers:
                        curr.orelse.append(maybe_ws)
                        curr = maybe_ws
                        i = next_idx
                        if node.name in ("for", "foreach", "recursive"):
                            break
                        continue
                    break
                new_nodes.append(chain)
                i += 1
                continue
            else:
                new_nodes.append(node)
                i += 1
        return new_nodes

    def parse_node(self, current_depth: int = 0) -> Node | None:
        if current_depth > MAX_PARSE_DEPTH:
            token = self.peek()
            raise TemplateSyntaxError(
                f"Maximum template nesting depth exceeded (max {MAX_PARSE_DEPTH}).",
                line=token.line if hasattr(token, "line") else 0,
                column=token.column if hasattr(token, "column") else 0,
                name=self.name,
                filename=self.filename,
            )

        token = self.peek()

        if token.type == TokenType.DIRECTIVE:
            directive_token = self.advance()
            expression = None
            if self.peek().type == TokenType.EXPRESSION:
                expression = self.advance().value

            block_directives = (
                "if",
                "unless",
                "else",
                "elif",
                "elseif",
                "else_if",
                "while",
                "for",
                "foreach",
                "switch",
                "case",
                "default",
                "auth",
                "guest",
                "htmx",
                "non_htmx",
                "fragment",
                "push",
                "verbatim",
                "section",
                "block",
                "slot",
                "component",
                "error",
                "messages",
                "even",
                "odd",
                "first",
                "last",
                "can",
                "cannot",
                "role",
                "permission",
                "form",
                "field",
                "button",
                "input",
                "php",
                "inject",
                "status",
                "reactive",
                "recursive",
            )

            standalone_directives = ("break", "continue", "child", "recurse")
            if directive_token.value in standalone_directives:
                return DirectiveNode(
                    name=directive_token.value,
                    expression=expression,
                    line=directive_token.line,
                    column=directive_token.column,
                )

            if directive_token.value in block_directives:
                saved_pos = self.pos
                ws_nodes = []
                while self.peek().type == TokenType.TEXT and self.peek().value.isspace():
                    ws_nodes.append(TextNode(content=self.advance().value))

                if self.peek().type == TokenType.BLOCK_OPEN:
                    self.advance()  # consume {
                    body = []
                    # Track nesting depth for proper brace matching
                    depth = 1
                    # Safety guard: prevent infinite loops on malformed blocks
                    _last_pos = self.pos
                    while depth > 0 and self.peek().type != TokenType.EOF:
                        # Check for nested opens/closes
                        if self.peek().type == TokenType.BLOCK_OPEN:
                            # This is an inner block — will be handled by recursive parse_node
                            pass

                        if self.peek().type == TokenType.BLOCK_CLOSE:
                            depth -= 1
                            if depth == 0:
                                break

                        n = self.parse_node(current_depth=current_depth + 1)
                        if n:
                            body.append(n)

                        if self.pos == _last_pos:  # Parser stalled
                            # Preserve the dropped token as text to avoid silent content loss
                            stalled_token = self.advance()
                            body.append(TextNode(content=stalled_token.value))
                        _last_pos = self.pos

                    if self.peek().type == TokenType.EOF:
                        # Try to show the problematic line
                        line_content = ""
                        if self.source and directive_token.line > 0:
                            lines = self.source.splitlines()
                            if 0 < directive_token.line <= len(lines):
                                line_content = lines[directive_token.line - 1].strip()[:80]
                        msg = f"Unclosed block for @{directive_token.value}. Expected '}}'."
                        if line_content:
                            msg += f" Found: {line_content}"
                        raise TemplateSyntaxError(
                            msg,
                            line=directive_token.line,
                            column=directive_token.column,
                            name=self.name,
                            filename=self.filename,
                        )

                    if self.peek().type == TokenType.BLOCK_CLOSE:
                        self.advance()  # consume }

                    # Group conditionals recursively within the body
                    grouped_body = self._group_conditionals(body)

                    return DirectiveNode(
                        name=directive_token.value,
                        expression=expression,
                        body=grouped_body,
                        line=directive_token.line,
                        column=directive_token.column,
                    )
                else:
                    self.pos = saved_pos

            return DirectiveNode(
                name=directive_token.value,
                expression=expression,
                line=directive_token.line,
                column=directive_token.column,
            )

        elif token.type == TokenType.BLOCK_CLOSE:
            return TextNode(content=self.advance().value)
        else:
            t = self.advance()
            content = t.value
            if t.type == TokenType.ESCAPED_AT:
                content = "@"
            return TextNode(content=content)
