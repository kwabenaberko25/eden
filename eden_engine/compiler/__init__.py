"""
Eden Template Compiler

Transforms source templates → AST → executable Python code

Modules:
  - codegen: AST → Python bytecode/code generation
"""

from .codegen import (
    CodeGenerator,
    CodeGenContext,
    Bytecode,
    BytecodeOp,
    ASTVisitor,
)

__all__ = [
    'CodeGenerator',
    'CodeGenContext',
    'Bytecode',
    'BytecodeOp',
    'ASTVisitor',
]
