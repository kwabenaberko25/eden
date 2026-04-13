#!/usr/bin/env python3
import sys
import py_compile

files_to_check = [
    "eden/admin/views.py",
    "eden/admin/__init__.py",
    "eden/admin/models.py",
]

all_ok = True
for filepath in files_to_check:
    try:
        py_compile.compile(filepath, doraise=True)
        print(f"✓ {filepath} - Syntax OK")
    except py_compile.PyCompileError as e:
        print(f"✗ {filepath} - Syntax Error:")
        print(f"  {e}")
        all_ok = False

sys.exit(0 if all_ok else 1)
