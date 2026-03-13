"""
Eden Templating Engine - Lexer Module

Provides tokenization of Eden templates using Lark parser.

Key Classes:
  - EdenLexer: Main tokenizer wrapping Lark grammar
  - SourceLocation: Source location tracking (line, column)
  - Token: Token representation
  - TokenizationError: Tokenization error with location info

Usage:
    from eden_engine.lexer import EdenLexer, TokenizationError
    
    lexer = EdenLexer()
    try:
        tree = lexer.tokenize("@if(x) { content }")
    except TokenizationError as e:
        print(e)  # Detailed error with location
"""

from .tokenizer import (
    EdenLexer,
    SourceLocation,
    Token,
    TokenizationError,
    create_lexer,
    tokenize
)

__all__ = [
    'EdenLexer',
    'SourceLocation',
    'Token',
    'TokenizationError',
    'create_lexer',
    'tokenize'
]

