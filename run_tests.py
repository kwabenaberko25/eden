#!/usr/bin/env python
import subprocess
import sys

result = subprocess.run([
    sys.executable, "-m", "pytest", 
    "tests/", 
    "-v", 
    "--tb=short",
    "-x"  # Stop on first failure to see what's happening
], cwd="c:\\PROJECTS\\eden-framework")

sys.exit(result.returncode)
