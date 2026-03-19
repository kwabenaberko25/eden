import ast
import os
import sys
import json
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict

@dataclass
class FunctionInfo:
    name: str
    args: List[str]
    docstring: Optional[str]
    returns: Optional[str]
    is_async: bool

@dataclass
class ClassInfo:
    name: str
    docstring: Optional[str]
    methods: List[FunctionInfo]
    bases: List[str]

def extract_from_file(filepath: str) -> Dict:
    with open(filepath, "r", encoding="utf-8") as f:
        node = ast.parse(f.read())

    classes = []
    functions = []

    for item in node.body:
        if isinstance(item, ast.ClassDef):
            methods = []
            for sub_item in item.body:
                if isinstance(sub_item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    methods.append(FunctionInfo(
                        name=sub_item.name,
                        args=[arg.arg for arg in sub_item.args.args],
                        docstring=ast.get_docstring(sub_item),
                        returns=ast.unparse(sub_item.returns) if sub_item.returns else None,
                        is_async=isinstance(sub_item, ast.AsyncFunctionDef)
                    ))
            
            classes.append(ClassInfo(
                name=item.name,
                docstring=ast.get_docstring(item),
                methods=methods,
                bases=[ast.unparse(base) for base in item.bases]
            ))
            
        elif isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append(FunctionInfo(
                name=item.name,
                args=[arg.arg for arg in item.args.args],
                docstring=ast.get_docstring(item),
                returns=ast.unparse(item.returns) if item.returns else None,
                is_async=isinstance(item, ast.AsyncFunctionDef)
            ))

    return {
        "classes": [asdict(c) for c in classes],
        "functions": [asdict(f) for f in functions]
    }

def format_as_markdown(data: Dict, filename: str) -> str:
    md = [f"# 🌿 API Data Sheet: `{filename}`\n"]
    
    if data["classes"]:
        md.append("## Classes\n")
        for cls in data["classes"]:
            md.append(f"### `class {cls['name']}`\n")
            if cls["docstring"]:
                md.append(f"{cls['docstring']}\n")
            if cls["bases"]:
                md.append(f"**Bases**: `{', '.join(cls['bases'])}`\n")
            
            if cls["methods"]:
                md.append("#### Methods\n")
                for method in cls["methods"]:
                    async_prefix = "async " if method["is_async"] else ""
                    md.append(f"- **`{async_prefix}{method['name']}({', '.join(method['args'])})`**")
                    if method["returns"]:
                        md.append(f" -> `{method['returns']}`")
                    md.append("\n")
                    if method["docstring"]:
                        md.append(f"  > {method['docstring'].splitlines()[0] if method['docstring'] else ''}\n")
            md.append("\n")

    if data["functions"]:
        md.append("## Functions\n")
        for func in data["functions"]:
            async_prefix = "async " if func["is_async"] else ""
            md.append(f"### ` {async_prefix}{func['name']}({', '.join(func['args'])})`\n")
            if func["returns"]:
                md.append(f"**Returns**: `{func['returns']}`\n")
            if func["docstring"]:
                md.append(f"{func['docstring']}\n")
            md.append("\n")
            
    return "".join(md)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python doc_extractor.py <path_to_python_file>")
        sys.exit(1)
        
    target_path = sys.argv[1]
    if not os.path.exists(target_path):
        print(f"Error: {target_path} not found.")
        sys.exit(1)
        
    try:
        results = extract_from_file(target_path)
        print(format_as_markdown(results, os.path.basename(target_path)))
    except Exception as e:
        print(f"Error parsing file: {e}")
        sys.exit(1)
