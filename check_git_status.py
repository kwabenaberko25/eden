#!/usr/bin/env python
import subprocess
import os

os.chdir(r"c:\PROJECTS\eden-framework")

# Get recent commits
print("Recent commits:")
result = subprocess.run(["git", "log", "--oneline", "-10"], capture_output=True, text=True)
print(result.stdout)

# Get status
print("\nGit status:")
result = subprocess.run(["git", "status", "--short"], capture_output=True, text=True)
print(result.stdout)

# Get diff stat
print("\nDiff stat:")
result = subprocess.run(["git", "diff", "--cached", "--stat"], capture_output=True, text=True)
print(result.stdout)
