"""
Scan project templates for directive usage and report on what's being used
"""
import re
from pathlib import Path
from collections import defaultdict

def scan_templates():
    """Scan all templates in the project for @directive usage"""
    
    template_dirs = [
        Path("templates"),
        Path("app/templates"),
        Path("tests/templates"),
        Path("examples"),
        Path("forge_audit_v2"),
        Path("test_prod"),
        Path("test_minimal"),
    ]
    
    # Regex patterns for directives
    directive_patterns = {
        "@if": r'@if\s*\(',
        "@unless": r'@unless\s*\(',
        "@for": r'@for(?:each)?\s*\(',
        "@switch": r'@switch\s*\(',
        "@case": r'@case\s*\(',
        "@auth": r'@auth\s*\{',
        "@guest": r'@guest\s*\{',
        "@htmx": r'@htmx\s*\{',
        "@non_htmx": r'@non_htmx\s*\{',
        "@fragment": r'@fragment\s*\(',
        "@csrf": r'@csrf',
        "@checked": r'@checked\s*\(',
        "@selected": r'@selected\s*\(',
        "@disabled": r'@disabled\s*\(',
        "@readonly": r'@readonly\s*\(',
        "@render_field": r'@render_field\s*\(',
        "@let": r'@let\s+',
        "@url": r'@url\s*\(',
        "@active_link": r'@active_link\s*\(',
        "@old": r'@old\s*\(',
        "@json": r'@json\s*\(',
        "@dump": r'@dump\s*\(',
        "@span": r'@span\s*\(',
        "@css": r'@css\s*\(',
        "@js": r'@js\s*\(',
        "@vite": r'@vite\s*\(',
        "@extends": r'@extends\s*\(',
        "@include": r'@include\s*\(',
        "@section/@block": r'@(?:section|block)\s*\(',
        "@yield": r'@yield\s*\(',
        "@push": r'@push\s*\(',
        "@component": r'@component\s*\(',
        "@slot": r'@slot\s*\(',
        "@error": r'@error\s*\(',
        "@messages": r'@messages\s*\{',
        "@method": r'@method\s*\(',
        "@even/@odd/@first/@last": r'@(?:even|odd|first|last)\s*\{',
    }
    
    directive_usage = defaultdict(int)
    directive_files = defaultdict(list)
    total_files = 0
    total_lines = 0
    
    print("=" * 80)
    print("EDEN TEMPLATE DIRECTIVE USAGE SCAN")
    print("=" * 80)
    print()
    
    for template_dir in template_dirs:
        if not template_dir.exists():
            continue
        
        print(f"\nScanning: {template_dir}/")
        print("-" * 80)
        
        templates = list(template_dir.rglob("*.html"))
        if not templates:
            print(f"  No templates found")
            continue
        
        for template_file in templates:
            total_files += 1
            try:
                content = template_file.read_text(encoding='utf-8', errors='ignore')
                lines = content.split('\n')
                total_lines += len(lines)
                
                # Check each directive pattern
                for directive, pattern in directive_patterns.items():
                    matches = re.findall(pattern, content)
                    if matches:
                        directive_usage[directive] += len(matches)
                        directive_files[directive].append(str(template_file))
                        
            except Exception as e:
                print(f"  ✗ Error reading {template_file}: {e}")
    
    # Report results
    print("\n" + "=" * 80)
    print("DIRECTIVE USAGE SUMMARY")
    print("=" * 80)
    print(f"\nTotal template files scanned: {total_files}")
    print(f"Total lines processed: {total_lines:,}")
    print()
    
    if directive_usage:
        print("Directives found in use:\n")
        for directive, count in sorted(directive_usage.items(), key=lambda x: x[1], reverse=True):
            print(f"  {directive:25} {count:4d} uses")
            if count <= 3:
                for fname in directive_files[directive]:
                    print(f"    - {fname}")
        
        print()
        print("Directives NOT found in use:")
        all_directives = set(directive_patterns.keys())
        used_directives = set(directive_usage.keys())
        unused = all_directives - used_directives
        
        if unused:
            for directive in sorted(unused):
                print(f"  {directive}")
        else:
            print("  All directives are used!")
    else:
        print("No @directives found. Scanned directories may not contain Eden templates.")
    
    print("\n" + "=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    
    # Provide recommendations based on findings
    if "@active_link" in directive_usage:
        print("\n✓ @active_link is actively used")
        print("  → Wildcard support now available (admin:*, blog:*, etc.)")
    else:
        print("\n! @active_link not found in templates")
        print("  → Consider adding it for better navigation highlighting:")
        print('     <a href="@url(\'dashboard\')" class="@active_link(\'dashboard\', \'active\')">Dashboard</a>')
    
    if "@checked" in directive_usage or "@selected" in directive_usage:
        print("\n✓ Form attribute directives (@checked, @selected, etc.) in use")
    else:
        print("\n! Form attribute directives not found")
        print("  → These make form handling cleaner:")
        print('     <input type="checkbox" @checked(user.agrees)>')
        print('     <option @selected(item.id == selected)>{{ item.name }}</option>')
    
    if not {"@auth", "@guest"}.intersection(directive_usage):
        print("\n! Authentication directives (@auth, @guest) not found")
        print("  → Useful for showing/hiding content based on login status:")
        print('     @auth { Secret content }\n     @guest { Please log in }')


if __name__ == "__main__":
    scan_templates()
