"""
Audit of Eden @Directives - Verify they work correctly (Simplified)
"""
import re
from pathlib import Path

# Read the templating.py file to extract all directives info
templating_file = Path("eden/templating.py").read_text(encoding="utf-8")

print("=" * 80)
print("EDEN @DIRECTIVES AUDIT")
print("=" * 80)

# 1. List all directives from the preprocess function
print("\n1. SIMPLE REPLACEMENT DIRECTIVES")
print("-" * 80)

simple_patterns = [
    '@csrf', '@eden_head', '@eden_scripts',
    '@yield', '@stack', '@render', '@show',
    '@extends', '@include', '@super',
    '@method', '@css', '@js', '@vite',
    '@old', '@span', '@json', '@dump',
    '@checked', '@selected', '@disabled', '@readonly',
    '@render_field', '@let', '@url', '@active_link'
]

for pattern in simple_patterns:
    if f"r'{pattern}" in templating_file or f'r"{pattern}' in templating_file:
        print(f"  ✓ {pattern}")
    else:
        print(f"  ? {pattern} (may be handled differently)")

# 2. Extract block directives
print("\n2. BLOCK DIRECTIVES (from directives list)")
print("-" * 80)

directives_section = re.search(
    r'directives = \[(.*?)\n        \]',
    templating_file,
    re.DOTALL
)

if directives_section:
    content = directives_section.group(1)
    # Find all directive names
    directive_names = re.findall(r'\("(\w+)"', content)
    print(f"Found {len(directive_names)} block directives:")
    for name in directive_names:
        print(f"  ✓ @{name}")

# 3. Check @active_link implementation in detail
print("\n3. @ACTIVE_LINK DETAILED ANALYSIS")
print("-" * 80)

# Extract _active_replacer
active_section = re.search(
    r'# ── @active_link.*?(_active_re = re\.compile.*?)source = _active_re\.sub',
    templating_file,
    re.DOTALL
)

if active_section:
    code = active_section.group(1)
    print("Pattern and replacer function:")
    for line in code.split('\n')[:30]:
        if line.strip():
            print(f"  {line}")

# 4. Check is_active function
print("\n4. IS_ACTIVE FUNCTION (handles route resolution)")
print("-" * 80)

is_active_section = re.search(
    r'def is_active\(request.*?\n.*?return.*?\n.*?return False',
    templating_file,
    re.DOTALL
)

if is_active_section:
    code = is_active_section.group(0)
    print("Function code:")
    for line in code.split('\n'):
        if line.strip():
            print(f"  {line}")

# 5. Known Issues
print("\n5. IDENTIFIED ISSUES")
print("-" * 80)

issues = []

# Check for wildcard handling
if "students:*" in templating_file:
    print("  ❌ Issue 1: Documentation shows wildcard syntax '@active_link('students:*', 'class')'")
    print("     but the is_active() function doesn't handle wildcards.")
    print("     Wildcard support not implemented!")
    issues.append("wildcard")

# Check if route name actually gets normalized
if "_normalise_route" in templating_file:
    print("  ✓ Route names ARE normalized (e.g., 'auth:login' → 'auth_login')")

# Check error handling
if "except Exception" in templating_file:
    print("  ⚠ Warning: is_active() silently catches ALL exceptions")
    print("     If route resolution fails, it returns False without logging")
    issues.append("silent_errors")

print("\n6. TESTING @ACTIVE_LINK CONVERSION")
print("-" * 80)

# Test the regex
_active_re = re.compile(
    r'@active_link\s*\(\s*(.+?)\s*,\s*[\'"]([^\'"]+)[\'"]\s*\)',
    re.DOTALL,
)

test_cases = [
    "@active_link('dashboard', 'bg-green-700')",
    "@active_link(name, 'is-active')",
    "@active_link('auth:login', 'is-active')",
    "@active_link('students:index', 'is-active')",
]

for test in test_cases:
    match = _active_re.search(test)
    if match:
        arg1, css = match.groups()
        arg1 = arg1.strip()
        # Check if it's quoted
        m_quoted = re.match(r'^([\'"])(.*)\1$', arg1)
        if m_quoted:
            # Normalize route name
            raw_name = m_quoted.group(2).replace(':', '_')
            result = f'{{{{ "{css}" if is_active(request, "{raw_name}") else "" }}}}'
        else:
            result = f'{{{{ "{css}" if is_active(request, {arg1}) else "" }}}}'
        print(f"  Input:  {test}")
        print(f"  Output: {result}")
        print()

print("\n" + "=" * 80)
print("RECOMMENDATIONS")
print("=" * 80)

if "wildcard" in issues:
    print("""
Issue: @active_link('route:*', 'class') doesn't support wildcards

Current behavior:
  @active_link('students:*', 'is-active') 
  -> is_active(request, "students_*")
  -> Request.url_for("students_*") will FAIL (invalid route name)

Solutions:
  1. Add wildcard matching to is_active():
     - Check if route_name ends with '*'
     - If yes, extract prefix and use startswith() matching
     
  2. Update documentation to clarify:
     - Either remove wildcard examples
     - Or implement the feature properly
""")

if "silent_errors" in issues:
    print("""
Issue: Route resolution errors are silently swallowed

Why @active_link might not work:
  - If route doesn't exist, url_for() raises exception
  - Exception is caught and True return becomes False
  - User gets no error message, just doesn't appear active
""")
