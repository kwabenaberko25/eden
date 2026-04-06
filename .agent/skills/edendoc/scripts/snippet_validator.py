import re
import os
import sys
import tempfile
import subprocess
from typing import List, Tuple

def extract_code_blocks(md_content: str) -> List[Tuple[str, int]]:
    """Extract code blocks and their line numbers from markdown."""
    pattern = r"```python\s*(.*?)\s*```"
    matches = re.finditer(pattern, md_content, re.DOTALL)
    
    blocks = []
    for match in matches:
        snippet = match.group(1)
        # Strip blockquote prefixes if present (e.g. within > [!TIP] blocks)
        lines = snippet.splitlines()
        clean_lines = []
        for line in lines:
            if line.startswith("> "):
                clean_lines.append(line[2:])
            elif line.startswith(">"):
                clean_lines.append(line[1:])
            else:
                clean_lines.append(line)
        
        snippet = "\n".join(clean_lines)
        start_pos = match.start()
        line_num = md_content.count('\n', 0, start_pos) + 1
        blocks.append((snippet, line_num))
    
    return blocks

def validate_snippet(snippet: str, line_offset: int, filename: str) -> bool:
    """Check if a snippet compiles and runs cleanly."""
    runnable_snippet = snippet
    if "await " in snippet:
        # Wrap async snippets
        indented = "\n".join(f"    {line}" for line in snippet.splitlines())
        runnable_snippet = (
            "import asyncio\n"
            "async def _snippet_test():\n"
            f"{indented}\n\n"
            "if __name__ == '__main__':\n"
            "    try:\n"
            "        asyncio.run(_snippet_test())\n"
            "    except Exception as e:\n"
            "        import sys\n"
            "        # Ignore expected missing-session errors in docs\n"
            "        ignore_errors = ['Session: Pass a session', 'not initialized']\n"
            "        msg = str(e)\n"
            "        if any(err in msg for err in ignore_errors):\n"
                "            sys.exit(0)\n"
            "        print(f'Runtime Error: {e}', file=sys.stderr)\n"
            "        sys.exit(1)\n"
        )

    with tempfile.NamedTemporaryFile(suffix=".py", mode='w', delete=False, encoding='utf-8') as tmp_file:
        tmp_file.write(runnable_snippet)
        tmp_path = tmp_file.name

    try:
        compile(runnable_snippet, '<snippet>', 'exec')
        
        env = os.environ.copy()
        env["PYTHONPATH"] = os.pathsep.join([os.getcwd(), env.get("PYTHONPATH", "")])
        env["EDEN_ENV"] = "test"

        result = subprocess.run(
            [sys.executable, tmp_path],
            capture_output=True,
            text=True,
            timeout=10,
            env=env
        )
        
        if result.returncode != 0:
            stderr_out = result.stderr
            ignore_errors = [
                'Session: Pass a session', 
                'not initialized',
                'WARNING:  You must pass the application as an import string',
                'ImportWarning',
                'DeprecationWarning',
            ]
            if not any(err in stderr_out for err in ignore_errors):
                print(f"FAILED [L{line_offset}] Snippet in {filename}:")
                print(f"--- Error ---\n{stderr_out}\n--------------")
                return False
            
    except SyntaxError as e:
        l_no = e.lineno or 1
        print(f"SYNTAX ERROR [L{line_offset + l_no - 1}] in {filename}: {e}")
        return False
    except subprocess.TimeoutExpired:
        print(f"TIMEOUT [L{line_offset}]")
        return False
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
            
    return True

def main(files: List[str]):
    all_passed = True
    for file_path in files:
        if not os.path.exists(file_path):
            print(f"Warning: {file_path} NOT FOUND")
            continue
            
        print(f"Validating: {os.path.basename(file_path)}")
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        snippets = extract_code_blocks(content)
        if not snippets:
            continue
            
        for snippet, line_num in snippets:
            if not validate_snippet(snippet, line_num, file_path):
                all_passed = False
    
    if all_passed:
        print("ALL PASSED")
        sys.exit(0)
    else:
        print("FAILED")
        sys.exit(1)

if __name__ == "__main__":
    main(sys.argv[1:])
