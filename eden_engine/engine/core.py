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
        
        Full pipeline: template_text -> lexer -> parser -> codegen -> runtime -> HTML
        
        Args:
            template_text: Template string
            context: Template context variables
        
        Returns:
            Rendered HTML output
            
        Raises:
            ValueError: If required components are not available
        """
        if not PARSER_AVAILABLE:
            return f"[Error: Parser not available: {PARSER_ERROR}]"
        if not CODEGEN_AVAILABLE:
            return f"[Error: CodeGenerator not available: {CODEGEN_ERROR}]"
        if not RUNTIME_AVAILABLE:
            return f"[Error: Runtime not available: {RUNTIME_ERROR}]"
        
        try:
            # Step 1: Parse template to AST
            from eden_engine.parser import parse
            from eden_engine.compiler.codegen import CodeGenerator
            
            ast = parse(template_text)
            
            # Step 2: Generate Python code from AST
            codegen = CodeGenerator()
            compiled_code = codegen.generate(ast)
            
            # Step 3: Execute compiled code with context
            result = self.runtime.execute(compiled_code, context)
            return result
            
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            return f"[Render Error: {str(e)}\n{error_trace}]"
    
    def render_sync(self, template_text: str, context: Dict[str, Any]) -> str:
        """Synchronous render (same as render, for clarity)"""
        return self.render(template_text, context)
