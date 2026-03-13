"""
Eden Templating Engine - Lexer/Tokenizer

This module provides lexical analysis for Eden templates using the Lark parser.
It wraps the grammar specification and provides a clean interface for tokenization
with comprehensive error reporting including accurate line/column numbers.

The tokenizer converts template strings into token streams that are consumed
by the parser to build the Abstract Syntax Tree (AST).

Grammar: eden_engine/grammar/eden_directives.lark
"""

import os
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any, NamedTuple
from lark import Lark, Tree, Token as LarkToken, v_args, Transformer
from lark.exceptions import LarkError, UnexpectedCharacters, UnexpectedToken, UnexpectedEOF


class SourceLocation(NamedTuple):
    """Represents a location in the source template."""
    line: int
    column: int
    
    def __str__(self) -> str:
        return f"Line {self.line}, Column {self.column}"


class Token(NamedTuple):
    """Represents a token in the token stream."""
    type: str
    value: str
    location: SourceLocation
    
    def __str__(self) -> str:
        return f"{self.type}({repr(self.value)}) @ {self.location}"


class TokenizationError(Exception):
    """Raised when tokenization fails."""
    pass


class EdenLexer:
    """
    Tokenizes Eden template strings using the Lark parser grammar.
    
    Features:
      - Wraps eden_directives.lark grammar
      - Accurate line/column error reporting
      - Supports all 40+ Eden directives
      - Handles Ghana-specific phone/currency formats
      - Provides detailed error messages for debugging
    
    Usage:
        lexer = EdenLexer()
        tokens = lexer.tokenize("@if(x) { content }")
        
    Error Handling:
        try:
            tokens = lexer.tokenize(template_string)
        except TokenizationError as e:
            print(e)  # Detailed error with line/column
    """
    
    _grammar_cache: Optional[Lark] = None  # Class-level cache for grammar
    
    def __init__(self):
        """Initialize the tokenizer by loading the Lark grammar."""
        self.source = ""
        self.line_map: Dict[int, int] = {}  # pos_in_stream → line_number
        self.parser = self._load_grammar()
    
    @classmethod
    def _load_grammar(cls) -> Lark:
        """
        Load and cache the Lark grammar from eden_directives.lark.
        
        Grammar location: eden_engine/grammar/eden_directives.lark
        
        Returns:
            Lark parser instance configured for Eden templates
            
        Raises:
            FileNotFoundError: If grammar file not found
            LarkError: If grammar is invalid
        """
        if cls._grammar_cache is not None:
            return cls._grammar_cache
        
        # Locate grammar file relative to this module
        current_dir = Path(__file__).parent.parent
        grammar_path = current_dir / "grammar" / "eden_directives.lark"
        
        if not grammar_path.exists():
            raise FileNotFoundError(
                f"Eden grammar not found at {grammar_path}\n"
                f"Expected: eden_engine/grammar/eden_directives.lark"
            )
        
        with open(grammar_path, 'r', encoding='utf-8') as f:
            grammar = f.read()
        
        try:
            parser = Lark(
                grammar,
                parser='lalr',
                start='template',
                propagate_positions=True,
                maybe_placeholders=False
            )
            cls._grammar_cache = parser
            return parser
        except LarkError as e:
            raise LarkError(
                f"Failed to parse Eden grammar at {grammar_path}:\n{str(e)}"
            )
    
    def _build_line_map(self) -> None:
        """
        Build mapping from byte position to line number for error reporting.
        
        Called once per tokenize() call to map stream positions to line numbers.
        Enables accurate error location reporting.
        """
        self.line_map.clear()
        line_num = 1
        
        for pos, char in enumerate(self.source):
            self.line_map[pos] = line_num
            if char == '\n':
                line_num += 1
        
        # Ensure last position is mapped
        self.line_map[len(self.source)] = line_num
    
    def get_location(self, pos: int) -> SourceLocation:
        """
        Get source location (line, column) for a position in the stream.
        
        Args:
            pos: Byte position in source
            
        Returns:
            SourceLocation with line and column
        """
        # Find line number from map
        line_num = self.line_map.get(pos, 1)
        
        # Find column within line
        # Search backwards for previous newline
        line_start_pos = 0
        for i in range(pos - 1, -1, -1):
            if self.source[i] == '\n':
                line_start_pos = i + 1
                break
        
        column = pos - line_start_pos
        return SourceLocation(line=line_num, column=column)
    
    def tokenize(self, template_string: str) -> Tree:
        """
        Tokenize an Eden template string.
        
        This method:
        1. Stores the source for error reporting
        2. Builds line mapping for accurate positioning
        3. Parses with Lark grammar
        4. Returns parse tree ready for parser traversal
        
        Args:
            template_string: The template to tokenize
            
        Returns:
            Lark parse Tree representing the template structure
            
        Raises:
            TokenizationError: On syntax errors (with line/column info)
            
        Examples:
            >>> lexer = EdenLexer()
            >>> tree = lexer.tokenize("@if(x) { {{ y }} }")
            >>> print(tree.pretty())
        """
        self.source = template_string
        self._build_line_map()
        
        try:
            tree = self.parser.parse(template_string)
            return tree
        except UnexpectedCharacters as e:
            location = self.get_location(e.pos_in_stream)
            char = self.source[e.pos_in_stream] if e.pos_in_stream < len(self.source) else 'EOF'
            expected = ', '.join(e.allowed) if e.allowed else 'unknown'
            
            raise TokenizationError(
                f"{location}: Unexpected character {repr(char)}\n"
                f"Expected one of: {expected}\n"
                f"Context: {self._get_error_context(e.pos_in_stream)}"
            )
        except UnexpectedToken as e:
            location = self.get_location(e.pos_in_stream)
            expected = ', '.join(e.expected) if e.expected else 'unknown'
            
            raise TokenizationError(
                f"{location}: Unexpected token {repr(e.token.value)}\n"
                f"Expected one of: {expected}\n"
                f"Context: {self._get_error_context(e.pos_in_stream)}"
            )
        except UnexpectedEOF as e:
            location = self.get_location(len(self.source))
            expected = ', '.join(e.expected if e.expected else ['content'])
            
            raise TokenizationError(
                f"{location}: Unexpected end of template\n"
                f"Expected: {expected}"
            )
        except LarkError as e:
            # Generic Lark error
            raise TokenizationError(f"Tokenization failed: {str(e)}")
        except Exception as e:
            # Catch any other exceptions
            raise TokenizationError(
                f"Unexpected error during tokenization: {str(e)}"
            )
    
    def _get_error_context(self, pos: int, context_width: int = 40) -> str:
        """
        Get surrounding context for error reporting.
        
        Args:
            pos: Position of error
            context_width: Characters to show on each side
            
        Returns:
            Formatted context string with error position marked
        """
        start = max(0, pos - context_width)
        end = min(len(self.source), pos + context_width)
        
        before = self.source[start:pos]
        after = self.source[pos:end]
        
        # Escape newlines for display
        before = before.replace('\n', '\\n')
        after = after.replace('\n', '\\n')
        
        return f"...{before}[HERE]{after}..."
    
    def get_line_count(self) -> int:
        """Get total number of lines in the tokenized source."""
        return max(self.line_map.values()) if self.line_map else 1
    
    def get_line(self, line_num: int) -> str:
        """
        Get a specific line from the source.
        
        Args:
            line_num: Line number (1-indexed)
            
        Returns:
            The line content (without newline)
            
        Raises:
            IndexError: If line number out of range
        """
        lines = self.source.split('\n')
        if line_num < 1 or line_num > len(lines):
            raise IndexError(f"Line {line_num} out of range (1-{len(lines)})")
        return lines[line_num - 1]


# ============================================================================
# PUBLIC API
# ============================================================================

def create_lexer() -> EdenLexer:
    """
    Factory function to create a new EdenLexer instance.
    
    Returns:
        Configured EdenLexer ready for tokenization
        
    Raises:
        FileNotFoundError: If grammar file not found
    """
    return EdenLexer()


def tokenize(template: str) -> Tree:
    """
    Convenience function to tokenize a template with default lexer.
    
    Args:
        template: Template string to tokenize
        
    Returns:
        Parse tree from Lark parser
        
    Raises:
        TokenizationError: If tokenization fails
    """
    lexer = EdenLexer()
    return lexer.tokenize(template)

