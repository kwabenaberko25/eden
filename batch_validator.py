import os
import subprocess
import sys

# Force UTF-8 output
if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

guides_dir = "docs/guides"
validator = ".agent/skills/edendoc/scripts/snippet_validator.py"

failed_files = []
passed_files = []

# Get all .md files in guides_dir
files = [f for f in os.listdir(guides_dir) if f.endswith(".md")]
files.sort()

print(f"Validating {len(files)} core guides...")

for filename in files:
    path = os.path.join(guides_dir, filename)
    print(f"Validating: {filename}", end=" ", flush=True)
    try:
        # Run validator
        result = subprocess.run(
            [sys.executable, validator, path],
            capture_output=True,
            text=True,
            encoding='utf-8' # Ensure encoding matches
        )
        if result.returncode == 0:
            print("PASSED")
            passed_files.append(filename)
        else:
            print("FAILED")
            failed_files.append((filename, result.stdout))
    except Exception as e:
        print(f"ERROR: {e}")
        failed_files.append((filename, str(e)))

print("\n--- Summary ---")
print(f"Total: {len(files)}")
print(f"Passed: {len(passed_files)}")
print(f"Failed: {len(failed_files)}")

if failed_files:
    print("\n--- Failures ---")
    for filename, output in failed_files:
        print(f"\n[{filename}]")
        # Print only the first error block from output
        lines = output.split("--- Error ---")
        if len(lines) > 1:
            for line in lines[1:]:
                # Check for Actual Error Message
                msg = line.split("--------------")[0].strip()
                if msg:
                     print(f"  - {msg.splitlines()[-1] if msg.splitlines() else msg}")
        else:
            print(f"  - {output.strip()}")
