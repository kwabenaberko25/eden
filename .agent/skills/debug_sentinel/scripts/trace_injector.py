import sys
import os
import argparse
from pathlib import Path

def inject_trace(filepath, line_number, var_name):
    filepath = Path(filepath)
    if not filepath.exists():
        print(f"File {filepath} not found.")
        return

    with open(filepath, "r") as f:
        lines = f.readlines()

    # Create backup
    backup_path = filepath.with_suffix(filepath.suffix + ".bak")
    if not backup_path.exists():
        with open(backup_path, "w") as f:
            f.writelines(lines)

    # 1-indexed to 0-indexed
    idx = line_number - 1
    if idx < 0 or idx >= len(lines):
        print(f"Line {line_number} is out of range.")
        return

    # Infer indentation
    current_line = lines[idx]
    indent = ""
    for char in current_line:
        if char.isspace():
            indent += char
        else:
            break

    # Inject print
    trace_line = f'{indent}print(f"DEBUG_TRACE: {var_name} at {filepath.name}:{line_number} -> {{repr({var_name})}}")\n'
    lines.insert(idx, trace_line)

    with open(filepath, "w") as f:
        f.writelines(lines)
    
    print(f"Injected trace for {var_name} in {filepath}:{line_number}")

def restore_trace(filepath):
    filepath = Path(filepath)
    backup_path = filepath.with_suffix(filepath.suffix + ".bak")
    
    if backup_path.exists():
        os.replace(backup_path, filepath)
        print(f"Restored {filepath} from backup.")
    else:
        print(f"No backup found for {filepath}.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inject/Restore debugging traces in Python files.")
    parser.add_argument("file", help="Path to the file to instrument")
    parser.add_argument("--line", type=int, help="Line number to inject trace (1-indexed)")
    parser.add_argument("--var", help="Variable name to trace")
    parser.add_argument("--restore", action="store_true", help="Restore the file from backup")

    args = parser.parse_args()

    if args.restore:
        restore_trace(args.file)
    elif args.line and args.var:
        inject_trace(args.file, args.line, args.var)
    else:
        parser.print_help()
