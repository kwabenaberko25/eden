
from __future__ import annotations
from dataclasses import dataclass, field
from .lexer import Token, TokenType

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
                "even", "odd", "first", "last", "can", "cannot", "role", "permission",
                "form", "field", "button", "input"
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
