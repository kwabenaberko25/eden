
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
        parser = TemplateParser(tokens)
        nodes = parser.parse()

        # 2. Compile AST to Jinja2
        compiler = TemplateCompiler()
        compiled = compiler.compile(nodes)

        # 4. Security: Automate target="_blank" protection
        def _enforce_noopener(m):
            tag = m.group(0)
            if 'rel=' not in tag.lower(): return tag[:-1] + ' rel="noopener noreferrer">'
            return tag
        compiled = re.sub(r'<a\s+[^>]*?target=[\'"]_blank[\'"][^>]*>', _enforce_noopener, compiled, flags=re.IGNORECASE)

        return compiled
