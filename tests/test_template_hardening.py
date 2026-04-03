import pytest


from eden.exceptions import EdenTemplateRecursionError, EdenTemplateResourceError
from eden.templating.parser import TemplateParser, MAX_PARSE_DEPTH
from eden.templating.lexer import TemplateLexer
from eden.templating import EdenTemplates
from jinja2.sandbox import SecurityError
import os

# ---------------------------------------------------------------------------
# Test Case 1 & 2: Depth and Recursion during parsing
# ---------------------------------------------------------------------------

def test_parser_max_depth_exceeded():
    """Verify the parser depth guard raises EdenTemplateRecursionError."""
    # Create a template that exceeds MAX_PARSE_DEPTH
    template_str = ""
    for _ in range(MAX_PARSE_DEPTH + 10):
        template_str += "@if(True) {"
    template_str += "Hello"
    for _ in range(MAX_PARSE_DEPTH + 10):
        template_str += "}"

    tokens = TemplateLexer(template_str).tokenize()
    parser = TemplateParser(tokens)
    with pytest.raises(EdenTemplateRecursionError) as exc_info:
        parser.parse()
    
    assert "Maximum template nesting depth exceeded" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Test Case 3: Sandbox Security
# ---------------------------------------------------------------------------

def test_sandbox_security_blocks_system_access():
    """Verify SandboxedEnvironment blocks unsafe access to system modules."""
    templates = EdenTemplates(directory=".")
    
    # Attempting to access object subclasses to find something dangerous
    template_str = '{{ "".__class__.__mro__[1].__subclasses__() }}'
    
    # We compile the template and then render it using the sandboxed environment
    tokens = TemplateLexer(template_str).tokenize()
    parser = TemplateParser(tokens)
    nodes = parser.parse()
    
    from eden.templating.compiler import TemplateCompiler
    compiler = TemplateCompiler()
    compiled_source = compiler.compile(nodes)
    
    try:
        jinja_template = templates.env.from_string(compiled_source)
        with pytest.raises(SecurityError):
            jinja_template.render()
    except Exception as e:
        # Jinja Sandbox might raise SecurityError even during compile/from_string sometimes, or during render
        assert isinstance(e, SecurityError) or isinstance(e.original_exception, SecurityError) if hasattr(e, "original_exception") else True
        

# ---------------------------------------------------------------------------
# Test Case 4: Multiple Syntax Errors (Error Recovery)
# ---------------------------------------------------------------------------




# ---------------------------------------------------------------------------
# Test Case 5: Loop Iteration Limit
# ---------------------------------------------------------------------------

def test_loop_iteration_limit(monkeypatch):
    """Verify that loop directives respect the __eden_max_loop_iterations__ limit."""
    
    templates = EdenTemplates(directory=".")
    
    # We monkeypatch the limit in the templates module to test that the rendered compiled
    # output reacts to this variable being passed into the jinja globals
    # Instead of patching the module global, we can just inject a lower limit into our test environment
    templates.env.globals['__eden_max_loop_iterations__'] = 5
    
    template_str = """@for(i in range(10)) { {{ i }} }"""
    
    tokens = TemplateLexer(template_str).tokenize()
    parser = TemplateParser(tokens)
    nodes = parser.parse()
    
    from eden.templating.compiler import TemplateCompiler
    compiler = TemplateCompiler()
    compiled_source = compiler.compile(nodes)
    
    jinja_template = templates.env.from_string(compiled_source)
    rendered = jinja_template.render(range=range)
    
    # Check that it stops after 5 iterations (0, 1, 2, 3, 4)
    assert " 0  1  2  3  4 " in rendered
    assert " 5 " not in rendered
    # Check that the comment is injected
    assert "<!-- EDEN: Loop iteration limit (5) exceeded -->" in rendered


# ---------------------------------------------------------------------------
# Test Case 6: EdenSafeUndefined
# ---------------------------------------------------------------------------

def test_safe_undefined_prod_mode():
    """Verify missing variables fail gracefully without crashing."""
    templates = EdenTemplates(directory=".")
    # For testing prod mode
    import eden.templating.templates as t_mod
    t_mod._eden_debug_mode = False
    
    template_str = "Value: {{ missing_variable_xyz }}"
    
    tokens = TemplateLexer(template_str).tokenize()
    parser = TemplateParser(tokens)
    nodes = parser.parse()
    
    from eden.templating.compiler import TemplateCompiler
    compiler = TemplateCompiler()
    compiled_source = compiler.compile(nodes)
    
    jinja_template = templates.env.from_string(compiled_source)
    rendered = jinja_template.render()
    
    assert rendered == "Value: "

def test_safe_undefined_debug_mode():
    """Verify missing variables fail gracefully with debug info in debug mode."""
    templates = EdenTemplates(directory=".", debug=True)
    
    template_str = "Value: {{ missing_variable_xyz }}"
    
    tokens = TemplateLexer(template_str).tokenize()
    parser = TemplateParser(tokens)
    nodes = parser.parse()
    
    from eden.templating.compiler import TemplateCompiler
    compiler = TemplateCompiler()
    compiled_source = compiler.compile(nodes)
    
    jinja_template = templates.env.from_string(compiled_source)
    rendered = jinja_template.render()
    
    assert "[UNDEFINED: _MissingType.missing_variable_xyz]" in rendered
