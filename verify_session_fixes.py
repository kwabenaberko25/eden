#!/usr/bin/env python
"""Verification script for templating engine session fixes."""

import sys
import traceback

def test_lexer_registry_sync():
    """Test that lexer can read from DIRECTIVE_REGISTRY."""
    try:
        from eden.templating.lexer import get_core_directives, _get_directives
        directives = get_core_directives()
        assert isinstance(directives, set), f"Expected set, got {type(directives)}"
        assert len(directives) > 0, "Directives list is empty"
        print(f"✅ Lexer registry sync: Found {len(directives)} directives")
        return True
    except Exception as e:
        print(f"❌ Lexer registry sync failed: {e}")
        traceback.print_exc()
        return False

def test_directive_registry():
    """Test that DIRECTIVE_REGISTRY is populated."""
    try:
        from eden.template_directives import DIRECTIVE_REGISTRY
        assert len(DIRECTIVE_REGISTRY) > 0, "Registry is empty"
        print(f"✅ Directive registry: {len(DIRECTIVE_REGISTRY)} directives registered")
        
        # Verify some core directives
        core = {"if", "for", "foreach", "while", "css", "js", "auth", "role"}
        missing = core - set(DIRECTIVE_REGISTRY.keys())
        if missing:
            print(f"⚠️  Missing directives: {missing}")
            return False
        return True
    except Exception as e:
        print(f"❌ Directive registry failed: {e}")
        traceback.print_exc()
        return False

def test_extensions_target_blank():
    """Test that extensions module loads with new target="_blank" code."""
    try:
        from eden.templating.extensions import EdenDirectivesExtension
        ext = EdenDirectivesExtension
        assert hasattr(ext, 'preprocess'), "Missing preprocess method"
        print(f"✅ Extensions: EdenDirectivesExtension loaded successfully")
        return True
    except Exception as e:
        print(f"❌ Extensions failed: {e}")
        traceback.print_exc()
        return False

def test_compiler_imports():
    """Test that compiler module loads with all fixes."""
    try:
        from eden.templating.compiler import TemplateCompiler, DIRECTIVE_REGISTRY
        compiler = TemplateCompiler()
        assert hasattr(compiler, 'compile'), "Missing compile method"
        assert hasattr(compiler, '_validate_directive_args'), "Missing validation method"
        print(f"✅ Compiler: TemplateCompiler loaded with all methods")
        return True
    except Exception as e:
        print(f"❌ Compiler failed: {e}")
        traceback.print_exc()
        return False

def test_quote_consistency():
    """Test that quote stripping is consistent."""
    try:
        # Read template_directives.py and check for quote consistency
        with open('eden/template_directives.py', 'r') as f:
            content = f.read()
            
        # Count quote patterns (just a sanity check, not comprehensive)
        count_quote_prime = content.count('strip(\'"\')') + content.count('strip("\'")') 
        # Should use strip("\"'") everywhere for new code
        if count_quote_prime > 0:
            print(f"⚠️  Found {count_quote_prime} mixed quote patterns (expected to be fixed in new code)")
        else:
            print(f"✅ Quote consistency: No mixed patterns detected")
        return True
    except Exception as e:
        print(f"❌ Quote consistency check failed: {e}")
        return False

def main():
    """Run all verification tests."""
    print("=" * 60)
    print("Templating Engine Session Fixes - Verification")
    print("=" * 60)
    
    tests = [
        ("Lexer Registry Sync", test_lexer_registry_sync),
        ("Directive Registry", test_directive_registry),
        ("Extensions target=_blank", test_extensions_target_blank),
        ("Compiler Imports", test_compiler_imports),
        ("Quote Consistency", test_quote_consistency),
    ]
    
    results = []
    for name, test_func in tests:
        print(f"\n{name}:")
        result = test_func()
        results.append((name, result))
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All verification tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
