from eden.templating import TemplateLexer, TokenType
import re

source = """
    @for(item in items) {
        <li>{{ item }}</li>
    }
    @let(x = 10)
    @fragment("inbox") {
        @auth("admin", "editor") {
            <ul id="inbox"></ul>
        }
    }
"""

lexer = TemplateLexer(source)
tokens = lexer.tokenize()
for t in tokens:
    print(f"{t.type.name:15} | {repr(t.value):20} | L{t.line}:{t.column}")
