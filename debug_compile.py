from eden.templating import TemplateLexer, TemplateParser, TemplateCompiler
import re

source = """
    @fragment("inbox") {
        @auth("admin", "editor") {
            <ul id="inbox"></ul>
        }
    }
"""

lexer = TemplateLexer(source)
tokens = lexer.tokenize()
parser = TemplateParser(tokens)
nodes = parser.parse()

compiler = TemplateCompiler()
for n in nodes:
    print(f"Node: {n}")
    res = compiler.visit(n)
    print(f"Result: {repr(res)}")
