#!/usr/bin/env python3
"""
Build Eden documentation and check for errors.
"""
import subprocess
import sys
import os

os.chdir(r"C:\PROJECTS\eden-framework")

print("=" * 70)
print("🔨 Building Eden Framework Documentation")
print("=" * 70)
print()

# Try to build with mkdocs
try:
    print("📚 Running: mkdocs build --strict")
    result = subprocess.run(
        [sys.executable, "-m", "mkdocs", "build", "--strict"],
        capture_output=False,
        text=True
    )
    
    if result.returncode == 0:
        print()
        print("=" * 70)
        print("✅ Documentation build SUCCESSFUL!")
        print("=" * 70)
        print()
        print("📁 Built files are in: docs/build/")
        print()
        sys.exit(0)
    else:
        print()
        print("=" * 70)
        print("❌ Documentation build FAILED")
        print("=" * 70)
        sys.exit(1)
        
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
