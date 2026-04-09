
import pytest
from eden.templating.lexer import TemplateLexer
from eden.templating.parser import TemplateParser
from eden.templating.compiler import TemplateCompiler

def compile_template(source: str) -> str:
    lexer = TemplateLexer(source)
    tokens = lexer.tokenize()
    parser = TemplateParser(tokens)
    nodes = parser.parse()
    compiler = TemplateCompiler()
    return compiler.compile(nodes)

def test_elseif_variants():
    # Test @elseif
    source = "@if(True) { Yes } @elseif(False) { No } @else { Maybe }"
    compiled = compile_template(source)
    assert "{% elif False %}" in compiled
    
    # Test @elif (alias)
    source = "@if(True) { Yes } @elif(False) { No } @else { Maybe }"
    compiled = compile_template(source)
    assert "{% elif False %}" in compiled
    
    # Test @else_if (new standardized variant)
    source = "@if(True) { Yes } @else_if(False) { No } @else { Maybe }"
    compiled = compile_template(source)
    assert "{% elif False %}" in compiled

def test_while_loop():
    source = "@while(count > 0) { {{ count }} @let count = count - 1 }"
    compiled = compile_template(source)
    # Check that it uses our for-break construct
    assert "{% for _ in range(__eden_max_loop_iterations__) %}" in compiled
    assert "{% if not (count > 0) %}" in compiled
    assert "{% break %}" in compiled
    assert "{{ count }}" in compiled
    assert "{% endfor %}" in compiled

def test_break_continue_conditional():
    # Test @break with condition
    source = "@for(i in items) { @break(i == 5) }"
    compiled = compile_template(source)
    assert "{% if i == 5 %}{% break %}{% endif %}" in compiled
    
    # Test @break without condition
    source = "@for(i in items) { @break }"
    compiled = compile_template(source)
    assert "{% break %}" in compiled
    
    # Test @continue with "if" prefix
    source = "@for(i in items) { @continue if (i < 2) }"
    compiled = compile_template(source)
    assert "{% if (i < 2) %}{% continue %}{% endif %}" in compiled

def test_empty_directive():
    # @empty is an alias for @else, used in @for loops (Blade style)
    source = "@for(user in users) { {{ user.name }} } @empty { No users }"
    compiled = compile_template(source)
    # Expected: {% for user in users %}{{ user.name }}{% else %}No users{% endfor %}
    assert "{% for user in users %}" in compiled
    assert "{% else %}" in compiled
    assert "No users" in compiled
    assert "{% endfor %}" in compiled

def test_inject_directive():
    # @inject(service, 'App\Services\Spark')
    source = "@inject(metrics, 'eden.services.Metrics')"
    compiled = compile_template(source)
    assert "{% set metrics = eden_dependency('eden.services.Metrics') %}" in compiled

def test_else_if_with_whitespace():
    source = "@if(a) { 1 } \n @else_if(b) { 2 }"
    compiled = compile_template(source)
    assert "{% elif b %}" in compiled
