"""
Eden Engine Core
Main templating engine (Phase 3)

Wires together:
  1. Lexer - tokenizes template text
  2. Parser - builds AST from tokens
  3. CodeGen - generates Python code from AST
  4. Runtime - executes compiled code with context
"""

import asyncio
from typing import Dict, Any, Optional

# Import pipeline components
try:
    from eden_engine.lexer import create_lexer
    LEXER_AVAILABLE = True
except ImportError as e:
    create_lexer = None
    LEXER_AVAILABLE = False
    LEXER_ERROR = str(e)

try:
    from eden_engine.parser import parse
    PARSER_AVAILABLE = True
except ImportError as e:
    parse = None
    PARSER_AVAILABLE = False
    PARSER_ERROR = str(e)

try:
    from eden_engine.compiler.codegen import CodeGenerator
    CODEGEN_AVAILABLE = True
except ImportError as e:
    CodeGenerator = None
    CODEGEN_AVAILABLE = False
    CODEGEN_ERROR = str(e)

try:
    from eden_engine.runtime.engine import TemplateEngine
    RUNTIME_AVAILABLE = True
except ImportError as e:
    TemplateEngine = None
    RUNTIME_AVAILABLE = False
    RUNTIME_ERROR = str(e)


class EdenEngine:
    """
    Main Eden templating engine
    
    Full pipeline:
    1. Lexer: template_text -> tokens
    2. Parser: tokens -> AST
    3. CodeGen: AST -> Python code
    4. Runtime: code + context -> HTML output
    """
    
    def __init__(self):
        """Initialize engine with all pipeline components"""
        self.lexer = create_lexer() if LEXER_AVAILABLE else None
        self.runtime = TemplateEngine() if RUNTIME_AVAILABLE else None
    
    def render(self, template_text: str, context: Dict[str, Any]) -> str:
        """
        Render a template with the given context.
        
        NOTE: High-level render() API is in development.
        Individual components (lexer, parser, runtime engine, filters, directives)
        are fully implemented and tested. They work independently and can be
        integrated into any pipeline.
        
        For now, use components directly:
        - from eden_engine.parser import EdenParser, parse
        - from eden_engine.runtime.engine import TemplateContext, FilterRegistry
        - from eden_engine.caching.cache import LRUCache
        
        Args:
            template_text: Template string
            context: Template context variables
        
        Returns:
            Rendered output (currently raises NotImplementedError)
        """
        raise NotImplementedError(
            "High-level render() API is in development. "
            "Use individual components directly - they are all working and tested. "
            r"See c:\eden_projects\eden_tests\README.md for examples."
        )
    
    def render_sync(self, template_text: str, context: Dict[str, Any]) -> str:
        """Synchronous render (same as render, for clarity)"""
        return self.render(template_text, context)
