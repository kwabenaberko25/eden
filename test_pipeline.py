#!/usr/bin/env python
"""Test the complete Eden templating pipeline"""

from eden_engine.lexer import create_lexer
from eden_engine.parser import parse
from eden_engine.compiler.codegen import CodeGenerator
from eden_engine.runtime.engine import TemplateEngine

# Test simple template
template_text = "Hello @if(name) { {{ name }} } @unless(name) { Guest }"
context = {"name": "World"}

try:
    # 1. Tokenize
    lexer = create_lexer()
    tokens = lexer.tokenize(template_text)
    print(f"✓ Lexer: Generated {len(tokens)} tokens")
    
    # 2. Parse
    ast = parse(template_text)
    print(f"✓ Parser: Generated AST")
    
    # 3. CodeGen
    codegen = CodeGenerator()
    code = codegen.generate(ast)
    print(f"✓ CodeGen: Generated code ({len(code)} chars)")
    
    # 4. Runtime
    engine = TemplateEngine()
    result = engine.execute(code, context)
    print(f"✓ Runtime: Result = '{result}'")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
