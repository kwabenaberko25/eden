"""
Eden Template Inheritance System

Modules:
  - inheritance: Template inheritance chain resolution, blocks, and yields
"""

from .inheritance import (
    BlockContent,
    TemplateChain,
    BlockManager,
    TemplateInheritanceResolver,
    TemplateLoader,
    FileSystemTemplateLoader,
    MemoryTemplateLoader,
    SectionManager,
    SuperResolver,
)

__all__ = [
    'BlockContent',
    'TemplateChain',
    'BlockManager',
    'TemplateInheritanceResolver',
    'TemplateLoader',
    'FileSystemTemplateLoader',
    'MemoryTemplateLoader',
    'SectionManager',
    'SuperResolver',
]
