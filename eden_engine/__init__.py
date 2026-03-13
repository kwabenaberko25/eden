"""
Eden Templating Engine
Main package
"""

__version__ = "0.1.0"
__author__ = "Eden Framework"

from .engine.core import EdenEngine
from .lexer.tokenizer import EdenLexer, tokenize
from .parser.parser import EdenParser, parse
from .parser.ast_nodes import *

__all__ = [
    'EdenEngine',
    'EdenLexer',
    'tokenize',
    'EdenParser',
    'parse',
]
