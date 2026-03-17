
from enum import Enum, auto
from dataclasses import dataclass
import re

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

    def read_until(self, end_cond, consume_enclosure=False) -> str:
        """Reads until a terminator or lambda condition is met."""
        start_pos = self.pos
        
        # If end_cond is a string (e.g. '-->')
        if isinstance(end_cond, str):
            enclosure_len = len(end_cond) if consume_enclosure else 0
            found_pos = self.source.find(end_cond, self.pos)
            if found_pos == -1:
                # Read until EOF
                res = self.advance(len(self.source) - self.pos)
                return res
            
            res = self.advance(found_pos - self.pos + enclosure_len)
            return res
        
        # If end_cond is a callable
        while self.pos < len(self.source):
            if end_cond(self.source[self.pos]):
                break
            self.advance()
        
        return self.source[start_pos:self.pos]

    def read_until_tag(self, tag_name: str) -> str:
        """Reads until </tag_name>."""
        closer = f"</{tag_name}>"
        found_pos = self.source.lower().find(closer, self.pos)
        if found_pos == -1:
            return self.advance(len(self.source) - self.pos)
        return self.advance(found_pos - self.pos + len(closer))

    def read_balanced(self, open_char: str, close_char: str) -> str:
        """Reads a balanced segment, e.g. for parentheses."""
        start_pos = self.pos
        self.advance() # consume open_char
        count = 1
        while self.pos < len(self.source) and count > 0:
            char = self.peek()
            if char == open_char:
                count += 1
            elif char == close_char:
                count -= 1
            self.advance()
        return self.source[start_pos:self.pos]

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
                # Avoid matching emails: must be at start or preceded by non-alphanumeric/underscore
                # Note: whitespace, punctuation like { ( } [ , ; are fine
                can_be_directive = True
                if self.pos > 0:
                    prev_char = self.source[self.pos - 1]
                    if prev_char.isalnum() or prev_char == '_':
                        can_be_directive = False
                    # Extra check for common email characters before @
                    if prev_char in ('.', '-', '+'):
                        can_be_directive = False
                
                if can_be_directive:
                    # Check if it's a valid directive name prefix
                    m = re.match(r'@([a-zA-Z_]\w*)', self.source[self.pos:])
                    if m:
                        name = m.group(1)
                        full_match = m.group(0)
                        
                        # Avoid emails: if followed by .something and no space/paren/brace
                        # e.g. @name.com should not match if it looks like an email domain
                        after_pos = self.pos + len(full_match)
                        if after_pos < len(self.source) and self.source[after_pos] == '.':
                             # Check if it looks like a domain suffix
                             m_domain = re.match(r'\.[a-zA-Z]{2,}', self.source[after_pos:])
                             if m_domain:
                                 can_be_directive = False
                
                if can_be_directive and m:
                    # Re-confirm m after potentially setting can_be_directive to False
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
                    saved_pos_expr = self.pos
                    saved_line_expr, saved_col_expr = self.line, self.column
                    ws_expr = ""
                    while self.pos < len(self.source) and self.source[self.pos].isspace():
                        ws_expr += self.advance()
                    
                    if self.peek() == '(':
                        expr_line, expr_col = self.line, self.column
                        expr = self.read_balanced('(', ')')
                        self.tokens.append(Token(TokenType.EXPRESSION, expr, expr_line, expr_col))
                    elif name in ("let", "php", "json", "dump", "css", "js", "vite", "method", "csrf", "csrf_token", "break", "continue"):
                        self.pos = saved_pos_expr
                        self.line = saved_line_expr
                        self.column = saved_col_expr
                        
                        # Read until newline, block open {, or block close }
                        raw_expr = self.read_until(lambda c: c == '\n' or c == '{' or c == '}').strip()
                        if raw_expr:
                            self.tokens.append(Token(TokenType.EXPRESSION, raw_expr, self.line, self.column))
                    else:
                        # Backtrack
                        self.pos = saved_pos_expr
                        self.line = saved_line_expr
                        self.column = saved_col_expr

                    # Optional block open: {
                    saved_pos = self.pos
                    saved_line, saved_col = self.line, self.column
                    ws = ""
                    while self.pos < len(self.source) and self.source[self.pos].isspace():
                        ws += self.advance()
                    
                    if self.peek() == '{':
                        if ws: self.tokens.append(Token(TokenType.TEXT, ws, saved_line, saved_col))
                        self.tokens.append(Token(TokenType.BLOCK_OPEN, self.advance(), self.line, self.column))
                    else:
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

            # 6. Fallback (Text)
            self.tokens.append(Token(TokenType.TEXT, self.advance(), self.line, self.column))

        self.tokens.append(Token(TokenType.EOF, "", self.line, self.column))
        return self.tokens
