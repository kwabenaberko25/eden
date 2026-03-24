import os
import sys
from datetime import datetime

def scaffold_doc(doc_type: str, title: str, output_path: str):
    """Generate a boilerplate doc based on the EdenDoc templates."""
    # Find the correct template
    template_name = "tutorial.md" if doc_type.lower() == "tutorial" else "recipe.md"
    template_path = os.path.join(os.path.dirname(__file__), "..", "templates", template_name)
    
    if not os.path.exists(template_path):
        print(f"Error: Template {template_name} not found.")
        sys.exit(1)
        
    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    # Replace the title placeholder
    content = content.replace("[Descriptive Title]", title).replace("[How to Do X?]", title)
    
    # Write the output file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)
        
    print(f"✅ Scaffolded {doc_type} at: {output_path}")

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python doc_scaffold.py <tutorial|recipe> <title> <output_path>")
        sys.exit(1)
        
    scaffold_doc(sys.argv[1], sys.argv[2], sys.argv[3])
