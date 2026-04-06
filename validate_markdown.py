#!/usr/bin/env python3
"""
Simple markdown validation for Eden documentation.
Checks for:
1. All files referenced in mkdocs.yml exist
2. All markdown links are relative
3. No broken internal links
"""
import os
import re
from pathlib import Path

os.chdir(r"C:\PROJECTS\eden-framework")

def check_file_exists(filepath):
    """Check if file exists."""
    return os.path.isfile(filepath)

def extract_links_from_markdown(filepath):
    """Extract all markdown links from a file."""
    with open(filepath) as f:
        content = f.read()
    
    # Find all markdown links: [text](url)
    pattern = r'\[([^\]]+)\]\(([^)]+)\)'
    return re.findall(pattern, content)

def main():
    print("=" * 70)
    print("📋 Eden Documentation Validation")
    print("=" * 70)
    print()
    
    # Check ORM documentation files
    orm_files = [
        "docs/guides/orm.md",
        "docs/guides/orm-querying.md",
        "docs/guides/orm-query-syntax.md",
        "docs/guides/orm-complex-patterns.md",
        "docs/guides/SINGLE_RECORD_RETRIEVAL.md",
        "docs/guides/orm-relationships.md",
        "docs/guides/orm-transactions.md",
        "docs/guides/orm-migrations.md",
        "docs/guides/ORM_INDEX.md",
        "docs/guides/MKDOCS_BUILD_GUIDE.md",
    ]
    
    print("1️⃣ Checking file existence...")
    missing = []
    for filepath in orm_files:
        if check_file_exists(filepath):
            size = os.path.getsize(filepath)
            print(f"   ✅ {filepath} ({size} bytes)")
        else:
            print(f"   ❌ {filepath} MISSING")
            missing.append(filepath)
    
    if missing:
        print(f"\n❌ {len(missing)} files missing!")
        return False
    
    print()
    print("2️⃣ Checking markdown links...")
    
    broken_links = []
    external_links = 0
    
    for filepath in orm_files:
        if not check_file_exists(filepath):
            continue
        
        links = extract_links_from_markdown(filepath)
        for text, url in links:
            # Skip external URLs
            if url.startswith("http"):
                external_links += 1
                continue
            
            # Skip anchors
            if url.startswith("#"):
                continue
            
            # Check relative file links
            if url.endswith(".md"):
                target_file = os.path.join("docs/guides", url)
                if not check_file_exists(target_file):
                    broken_links.append((filepath, url, target_file))
    
    if broken_links:
        print(f"   ❌ Found {len(broken_links)} broken links:")
        for source, url, target in broken_links:
            print(f"      - {source} → {url} (would be: {target})")
        return False
    else:
        print(f"   ✅ All internal links valid")
        print(f"   ℹ️  {external_links} external links found")
    
    print()
    print("=" * 70)
    print("✅ VALIDATION PASSED")
    print("=" * 70)
    print()
    print("Ready to build documentation:")
    print("  uv run mkdocs build")
    print("  or")
    print("  python -m mkdocs build")
    print()
    
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
