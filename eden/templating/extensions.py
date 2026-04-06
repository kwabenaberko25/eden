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

        # 4. Security: Automate target="_blank" protection
        def _enforce_noopener(m: re.Match[str]) -> str:
            tag = m.group(0)
            tag_lower = tag.lower()
            
            # Check if rel attribute exists
            if not re.search(r'rel\s*=\s*["\']', tag_lower):
                # No rel attribute, add it before the closing >
                return tag[:-1] + ' rel="noopener noreferrer">'
            
            # Check if rel contains noopener
            rel_match = re.search(r'rel\s*=\s*["\']([^"\']*)["\']', tag_lower)
            if rel_match:
                rel_value = rel_match.group(1)
                if 'noopener' not in rel_value:
                    # Add noopener to existing rel attribute
                    rel_end = rel_match.end()
                    return tag[:rel_end-1] + ' noopener noreferrer"' + tag[rel_end:]
            
            return tag

        # Match <a> tags with target="_blank" (case-insensitive, flexible spacing)
        compiled = re.sub(
            r'<a\s+[^>]*?target\s*=\s*["\']_blank["\'][^>]*?>',
            _enforce_noopener,
            compiled,
            flags=re.IGNORECASE,
        )

        return compiled
