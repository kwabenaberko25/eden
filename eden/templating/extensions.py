from __future__ import annotations
import re
from jinja2.ext import Extension
from .lexer import TemplateLexer
from .parser import TemplateParser
from .compiler import TemplateCompiler


class EdenDirectivesExtension(Extension):
    """
    Jinja2 extension that pre-processes Eden's modern syntax (@if, @for, etc.)
    Ensures that directives are not replaced within strings or comments.
    """

    def preprocess(self, source: str, name: str | None, filename: str | None = None) -> str:
        # 0. Tokenize
        lexer = TemplateLexer(source)
        tokens = lexer.tokenize()

        # 1. Parse into AST
        parser = TemplateParser(tokens, name=name, filename=filename, source=source)
        nodes = parser.parse()

        # 2. Compile AST to Jinja2
        compiler = TemplateCompiler()
        compiled = compiler.compile(nodes)

        return compiled
