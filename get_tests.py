import subprocess
import os

os.chdir("c:\\PROJECTS\\eden-framework")
result = subprocess.run(["python", "-m", "pytest", "tests/", "-v", "--tb=line", "-q"], 
                       capture_output=True, text=True)
print(result.stdout)
print(result.stderr)
