import subprocess

res = subprocess.run(["uv", "run", "pytest", "-q", "--tb=short"], capture_output=True, text=True)
with open("pytest_output_full.txt", "w", encoding="utf-8") as f:
    f.write(res.stdout)
