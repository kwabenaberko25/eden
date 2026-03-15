#!/usr/bin/env python
"""
Isolate Test Script

Extracts a failing pytest test into a standalone script for easier debugging.

Usage:
    python isolate-test.py tests/auth/test_login.py::TestLogin::test_invalid_credentials
    python isolate-test.py tests/db/test_orm.py::test_queryset_filter -o debug_test.py
"""

import argparse
import ast
import sys
from pathlib import Path
from typing import Optional


def parse_test_identifier(identifier: str) -> tuple[str, Optional[str], Optional[str]]:
    """Parse 'path/to/test.py::ClassName::method' into (path, class, method)."""
    parts = identifier.split("::")
    path = parts[0]
    class_name = parts[1] if len(parts) > 1 else None
    method_name = parts[2] if len(parts) > 2 else None
    return path, class_name, method_name


def extract_test_content(
    test_file: Path, class_name: Optional[str], method_name: Optional[str]
) -> str:
    """Extract test function or test class from file."""
    with open(test_file) as f:
        content = f.read()
    
    tree = ast.parse(content)
    
    # Find imports
    imports = []
    test_code = []
    
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            imports.append(ast.unparse(node))
    
    # Find test class or function
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and class_name and node.name == class_name:
            # Extract the class
            test_code.append(ast.unparse(node))
            break
        elif isinstance(node, ast.FunctionDef) and method_name and node.name == method_name:
            # Extract the function
            test_code.append(ast.unparse(node))
            break
    
    return "\n".join(imports) + "\n\n" + "\n".join(test_code)


def generate_debug_script(
    test_file: str,
    class_name: Optional[str],
    method_name: Optional[str],
    output_file: Optional[str] = None,
) -> str:
    """Generate standalone debug script from test file."""
    
    path = Path(test_file)
    if not path.exists():
        print(f"Error: Test file not found: {test_file}")
        sys.exit(1)
    
    # Extract test content
    test_content = extract_test_content(path, class_name, method_name)
    
    # Generate debug script
    script = f"""#!/usr/bin/env python
\"\"\"
Debug script extracted from: {test_file}
Test: {class_name + '::' if class_name else ''}{method_name or 'all'}

Run with:
    python {output_file or 'debug_test.py'} -xvs

Or with profiling:
    python -m cProfile -s cumtime {output_file or 'debug_test.py'}
\"\"\"

import asyncio
import logging
import sys
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(name)s - %(levelname)s - %(message)s"
)

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Test imports and setup
{test_content}


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-xvs"])
"""
    
    return script


def main():
    parser = argparse.ArgumentParser(
        description="Extract failing pytest test into standalone script"
    )
    parser.add_argument(
        "identifier",
        help="Test identifier: 'path/to/test.py::ClassName::method_name'",
    )
    parser.add_argument(
        "-o", "--output",
        help="Output file (default: debug_test.py)",
        default="debug_test.py",
    )
    parser.add_argument(
        "--run",
        action="store_true",
        help="Run the extracted test immediately",
    )
    
    args = parser.parse_args()
    
    # Parse identifier
    test_file, class_name, method_name = parse_test_identifier(args.identifier)
    
    # Generate script
    script = generate_debug_script(test_file, class_name, method_name, args.output)
    
    # Write output
    output_path = Path(args.output)
    output_path.write_text(script)
    print(f"✅ Generated: {output_path.absolute()}")
    print(f"\nRun with:")
    print(f"  python {args.output} -xvs")
    
    # Optionally run
    if args.run:
        import subprocess
        print(f"\nRunning...\n")
        subprocess.run([sys.executable, str(output_path)])


if __name__ == "__main__":
    main()
