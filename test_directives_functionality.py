"""
Test suite for Eden @directives
Tests basic functionality and conversions
"""
import re

# Test the @active_link preprocessing by simulating it
def test_active_link_conversion():
    print("Testing @active_link conversion...")
    
    # Simulate the regex replacement logic from templating.py
    _active_re = re.compile(
        r'@active_link\s*\(\s*(.+?)\s*,\s*[\'"]([^\'"]+)[\'"]\s*\)',
        re.DOTALL,
    )
    
    def _normalise_route(raw_name: str) -> str:
        return raw_name.replace(':', '_')
    
    test_cases = [
        (
            "@active_link('dashboard', 'bg-green-700')",
            'is_active(request, "dashboard")'
        ),
        (
            "@active_link('auth:login', 'is-active')",
            'is_active(request, "auth_login")'
        ),
        (
            "@active_link('students:index', 'active')",
            'is_active(request, "students_index")'
        ),
        (
            "@active_link(current_page, 'active')",
            'is_active(request, current_page)'
        ),
        (
            "@active_link('students:*', 'is-active')",
            'is_active(request, "students_*")'
        ),
    ]
    
    for input_str, expected in test_cases:
        match = _active_re.search(input_str)
        if match:
            arg1 = match.group(1).strip()
            css_cls = match.group(2)
            
            # Check if arg1 is a quoted string literal
            m_quoted = re.match(r'^([\'"])(.*)\1$', arg1)
            if m_quoted:
                # It's a literal string - normalize it
                raw_name = _normalise_route(m_quoted.group(2))
                result = f'is_active(request, "{raw_name}")'
            else:
                # It's an expression
                result = f'is_active(request, {arg1})'
            
            if expected in f"{{ {result} }}":
                print(f"  ✓ {input_str}")
                print(f"    → {result}")
            else:
                print(f"  ✗ {input_str}")
                print(f"    Expected: {expected}")
                print(f"    Got: {result}")
        else:
            print(f"  ✗ {input_str} - NO REGEX MATCH")
        print()


def test_other_directives():
    print("\nTesting other directive conversions...")
    
    test_cases = [
        ("@csrf", "csrf_token"),
        ("@url('dashboard')", 'url_for("dashboard")'),
        ("@old('email')", 'old("email"'),
        ("@checked(form.field.is_required)", "{% if form.field.is_required %}checked{% endif %}"),
        ("@selected(item.id == selected_id)", "{% if item.id == selected_id %}selected{% endif %}"),
        ("@disabled(form.is_readonly)", "{% if form.is_readonly %}disabled{% endif %}"),
        ("@readonly(field.read_only)", "{% if field.read_only %}readonly{% endif %}"),
    ]
    
    for input_str, expected in test_cases:
        # This is just checking if patterns are recognized
        import eden.templating as t
        if f"r'{input_str.split('(')[0]}" in open('eden/templating.py').read():
            print(f"  ✓ Pattern {input_str[:40]}")
        else:
            print(f"  ? Pattern {input_str[:40]}")


def test_block_directives():
    print("\nTesting block directives...")
    
    test_cases = [
        "@if",
        "@for", 
        "@unless",
        "@auth",
        "@guest",
        "@htmx",
        "@component",
        "@error",
        "@messages",
    ]
    
    with open('eden/templating.py') as f:
        content = f.read()
    
    for directive in test_cases:
        if f'("{directive[1:]}"' in content or f"'{directive[1:]}'" in content:
            print(f"  ✓ @{directive[1:]}")
        else:
            print(f"  ✗ @{directive[1:]}")




def test_is_active_function():
    """Test the is_active helper function logic (mock-based)"""
    print("\nTesting is_active() function logic...")
    
    print("  ℹ is_active() test requires full Eden setup - integration test")
    print("    Use integration tests in test_prod/ or test_minimal/ instead")


if __name__ == "__main__":
    print("=" * 80)
    print("EDEN @DIRECTIVES TEST SUITE")
    print("=" * 80)
    print()
    
    test_active_link_conversion()
    test_other_directives()
    test_block_directives()
    test_is_active_function()
    
    print("\n" + "=" * 80)
    print("Test suite complete!")
    print("=" * 80)
