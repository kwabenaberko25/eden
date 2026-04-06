#!/usr/bin/env python3
"""
Quick syntax verification for all modified templating files.
This verifies that the fixes don't introduce Python syntax errors.
"""

import sys
import traceback

def test_imports():
    """Test that all modified modules can be imported."""
    errors = []
    
    test_modules = [
        ('eden.templating.compiler', 'Compiler module'),
        ('eden.templating.lexer', 'Lexer module'),
        ('eden.templating.templates', 'Templates module'),
        ('eden.template_directives', 'Directives module'),
    ]
    
    for module_name, description in test_modules:
        try:
            print(f"Testing {description}...", end=" ")
            __import__(module_name)
            print("✅ OK")
        except SyntaxError as e:
            errors.append(f"SYNTAX ERROR in {module_name}: {e}")
            print(f"❌ SYNTAX ERROR")
        except ImportError as e:
            print(f"⚠️ IMPORT ERROR (may be expected)")
            errors.append(f"IMPORT ERROR in {module_name}: {e}")
        except Exception as e:
            print(f"❌ ERROR")
            errors.append(f"ERROR in {module_name}: {e}")
    
    return errors

def test_directive_registry():
    """Test that the directive registry can be loaded."""
    try:
        print("\nTesting DIRECTIVE_REGISTRY...", end=" ")
        from eden.template_directives import DIRECTIVE_REGISTRY
        
        if not DIRECTIVE_REGISTRY:
            print("❌ EMPTY")
            return ["DIRECTIVE_REGISTRY is empty"]
        
        # Check for key directives
        expected_directives = [
            'if', 'for', 'foreach', 'while', 'switch',
            'auth', 'can', 'role', 'admin',
            'csrf', 'form', 'inject', 'dump',
            'class', 'active_link', 'reactive', 'recursive',
            'error', 'status', 'let'
        ]
        
        missing = []
        for directive in expected_directives:
            if directive not in DIRECTIVE_REGISTRY:
                missing.append(directive)
        
        if missing:
            print(f"❌ Missing: {', '.join(missing)}")
            return [f"Missing directives: {missing}"]
        
        print(f"✅ OK ({len(DIRECTIVE_REGISTRY)} directives registered)")
        return []
    except Exception as e:
        print(f"❌ ERROR")
        return [f"Error loading DIRECTIVE_REGISTRY: {e}"]

def main():
    """Run all syntax verification tests."""
    print("=" * 60)
    print("TEMPLATING ENGINE SYNTAX VERIFICATION")
    print("=" * 60)
    
    errors = []
    
    # Test imports
    errors.extend(test_imports())
    
    # Test directive registry
    errors.extend(test_directive_registry())
    
    # Summary
    print("\n" + "=" * 60)
    if errors:
        print(f"❌ {len(errors)} ERROR(S) FOUND")
        for i, error in enumerate(errors, 1):
            print(f"\n{i}. {error}")
        return 1
    else:
        print("✅ ALL TESTS PASSED")
        return 0

if __name__ == '__main__':
    sys.exit(main())
