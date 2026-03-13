"""
Eden Template Inheritance System

Implements template inheritance with blocks, yields, and template chain support.

Architecture:
  - TemplateInheritanceResolver: Resolves template inheritance chains
  - BlockManager: Manages named blocks across template hierarchy  
  - TemplateChain: Represents inheritance chain (parent → child)
  - BlockContent: Represents block content and override information
"""

import asyncio
from typing import Dict, Optional, Set, List, Tuple
from dataclasses import dataclass, field
from abc import ABC, abstractmethod


@dataclass
class BlockContent:
    """Represents a template block with its content and metadata."""
    
    name: str
    content: str  # The block body text (raw template)
    level: int = 0  # Level in inheritance chain (0 = root parent)
    parent_name: Optional[str] = None  # Parent template name
    line_number: int = 0
    column_number: int = 0
    
    def __repr__(self) -> str:
        return f"Block(name={self.name}, level={self.level}, len={len(self.content)})"


@dataclass
class TemplateChain:
    """Represents a template inheritance chain (parent → child)."""
    
    templates: List[str] = field(default_factory=list)  # Template names/paths in order (parent first)
    blocks: Dict[str, BlockContent] = field(default_factory=dict)  # Blocks by name
    parent_blocks: Dict[str, BlockContent] = field(default_factory=dict)  # Blocks from parent (for @super)
    
    def add_template(self, name: str) -> None:
        """Add template to chain."""
        self.templates.append(name)
    
    def add_block(self, block: BlockContent) -> None:
        """Add block to chain."""
        self.blocks[block.name] = block
    
    def get_block(self, name: str) -> Optional[BlockContent]:
        """Get block by name."""
        return self.blocks.get(name)
    
    def get_parent_block(self, name: str) -> Optional[BlockContent]:
        """Get parent template's block."""
        return self.parent_blocks.get(name)
    
    def has_block(self, name: str) -> bool:
        """Check if block exists."""
        return name in self.blocks
    
    def chain_summary(self) -> str:
        """Get human-readable chain summary."""
        return " → ".join(self.templates)


class BlockManager:
    """
    Manages template blocks across inheritance hierarchy.
    
    Tracks block definitions, overrides, and super() resolution.
    """
    
    def __init__(self):
        self.blocks: Dict[str, Dict[str, BlockContent]] = {}  # template -> {name -> block}
        self.chain: Optional[TemplateChain] = None
    
    def register_block(self, template_name: str, block: BlockContent) -> None:
        """Register a block in a template."""
        if template_name not in self.blocks:
            self.blocks[template_name] = {}
        self.blocks[template_name][block.name] = block
    
    def get_block(self, template_name: str, block_name: str) -> Optional[BlockContent]:
        """Get block from template."""
        if template_name not in self.blocks:
            return None
        return self.blocks[template_name].get(block_name)
    
    def get_all_blocks(self, template_name: str) -> Dict[str, BlockContent]:
        """Get all blocks from template."""
        return self.blocks.get(template_name, {})
    
    def get_parent_block(self, block_name: str) -> Optional[BlockContent]:
        """Get parent template's version of block (for @super)."""
        if not self.chain or not self.chain.templates:
            return None
        
        # Find current template position in chain
        # Return block from parent template if exists
        for i in range(len(self.chain.templates) - 1):
            parent_template = self.chain.templates[i]
            blocks = self.get_all_blocks(parent_template)
            if block_name in blocks:
                return blocks[block_name]
        
        return None
    
    def resolve_block_value(self, template_name: str, block_name: str, 
                           context: Dict = None) -> str:
        """
        Resolve final block value (considering inheritance).
        
        Returns the most-derived (child) version of the block.
        """
        block = self.get_block(template_name, block_name)
        if block:
            return block.content
        return ""
    
    def list_blocks(self, template_name: str) -> List[str]:
        """List all block names in template."""
        blocks = self.get_all_blocks(template_name)
        return list(blocks.keys())


class TemplateInheritanceResolver:
    """
    Resolves template inheritance chains.
    
    Handles @extends directive and builds inheritance tree.
    """
    
    def __init__(self, loader=None):
        self.loader = loader  # External template loader
        self.chains: Dict[str, TemplateChain] = {}  # Cache of resolved chains
        self.block_manager = BlockManager()
    
    async def resolve_extends(self, template_name: str) -> Optional[TemplateChain]:
        """
        Resolve full inheritance chain for template.
        
        Returns TemplateChain with all parent templates in order.
        """
        if template_name in self.chains:
            return self.chains[template_name]
        
        chain = TemplateChain()
        visited = set()
        
        await self._build_chain(template_name, chain, visited)
        
        self.chains[template_name] = chain
        return chain
    
    async def _build_chain(self, template_name: str, chain: TemplateChain, 
                          visited: Set[str]) -> None:
        """Recursively build template chain."""
        if template_name in visited:
            raise ValueError(f"Circular template inheritance detected: {template_name}")
        
        visited.add(template_name)
        
        # Load template
        if not self.loader:
            return
        
        template_content = await self.loader.load(template_name)
        if not template_content:
            return
        
        # Check if template extends parent
        parent = self._extract_extends(template_content)
        
        if parent:
            # Recursively resolve parent
            await self._build_chain(parent, chain, visited)
        
        # Add this template to chain
        chain.add_template(template_name)
    
    @staticmethod
    def _extract_extends(template_content: str) -> Optional[str]:
        """Extract parent template name from @extends directive."""
        # Simplified - would use parser in real implementation
        import re
        match = re.search(r"@extends\s*\(\s*['\"]([^'\"]+)['\"]\s*\)", template_content)
        if match:
            return match.group(1)
        return None
    
    def register_block(self, template_name: str, block_name: str, 
                      content: str, level: int = 0) -> None:
        """Register a block in template."""
        block = BlockContent(name=block_name, content=content, level=level)
        self.block_manager.register_block(template_name, block)
    
    def get_chain(self, template_name: str) -> Optional[TemplateChain]:
        """Get cached chain."""
        return self.chains.get(template_name)
    
    def get_block_value(self, template_name: str, block_name: str) -> str:
        """Get final block value from inheritance chain."""
        return self.block_manager.resolve_block_value(template_name, block_name)
    
    def list_all_blocks(self, template_name: str) -> List[str]:
        """List all available blocks in template."""
        return self.block_manager.list_blocks(template_name)


class TemplateLoader(ABC):
    """Abstract base for template loading."""
    
    @abstractmethod
    async def load(self, template_name: str) -> Optional[str]:
        """Load template by name. Returns content or None."""
        pass
    
    @abstractmethod
    async def exists(self, template_name: str) -> bool:
        """Check if template exists."""
        pass


class FileSystemTemplateLoader(TemplateLoader):
    """Load templates from filesystem."""
    
    def __init__(self, base_path: str = "templates"):
        self.base_path = base_path
    
    async def load(self, template_name: str) -> Optional[str]:
        """Load template from filesystem."""
        import os
        import pathlib
        
        # Security: prevent path traversal
        safe_name = os.path.normpath(template_name)
        if ".." in safe_name:
            raise ValueError(f"Invalid template path: {template_name}")
        
        template_path = os.path.join(self.base_path, safe_name)
        if not template_path.endswith(('.html', '.jinja', '.eden')):
            template_path += '.html'
        
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                return f.read()
        except (FileNotFoundError, IOError):
            return None
    
    async def exists(self, template_name: str) -> bool:
        """Check if template file exists."""
        import os
        
        safe_name = os.path.normpath(template_name)
        template_path = os.path.join(self.base_path, safe_name)
        if not template_path.endswith(('.html', '.jinja', '.eden')):
            template_path += '.html'
        
        return os.path.exists(template_path)


class MemoryTemplateLoader(TemplateLoader):
    """Load templates from in-memory dictionary."""
    
    def __init__(self, templates: Dict[str, str] = None):
        self.templates = templates or {}
    
    async def load(self, template_name: str) -> Optional[str]:
        """Load template from memory."""
        return self.templates.get(template_name)
    
    async def exists(self, template_name: str) -> bool:
        """Check if template exists in memory."""
        return template_name in self.templates
    
    def add_template(self, name: str, content: str) -> None:
        """Add template to memory."""
        self.templates[name] = content


class SectionManager:
    """
    Manages template sections (similar to blocks but for content stacks).
    
    Used by @section and @yield directives.
    """
    
    def __init__(self):
        self.sections: Dict[str, List[str]] = {}  # section_name -> [content1, content2, ...]
    
    def push_section(self, name: str, content: str) -> None:
        """Push content onto section stack."""
        if name not in self.sections:
            self.sections[name] = []
        self.sections[name].append(content)
    
    def pop_section(self, name: str) -> Optional[str]:
        """Pop content from section stack."""
        if name not in self.sections or not self.sections[name]:
            return None
        return self.sections[name].pop()
    
    def get_section(self, name: str) -> Optional[str]:
        """Peek at top of section stack."""
        if name not in self.sections or not self.sections[name]:
            return None
        return self.sections[name][-1]
    
    def get_all_section_content(self, name: str) -> str:
        """Get all section content concatenated."""
        if name not in self.sections:
            return ""
        return "".join(self.sections[name])
    
    def clear_section(self, name: str) -> None:
        """Clear section stack."""
        if name in self.sections:
            self.sections[name] = []


class SuperResolver:
    """
    Resolves @super directive to parent block content.
    
    Enables child blocks to include parent block content.
    """
    
    def __init__(self, block_manager: BlockManager, chain: TemplateChain):
        self.block_manager = block_manager
        self.chain = chain
    
    def get_super_content(self, block_name: str) -> str:
        """Get parent block content for @super directive."""
        parent_block = self.block_manager.get_parent_block(block_name)
        if parent_block:
            return parent_block.content
        return ""
    
    def render_super(self, block_name: str, current_level: int) -> str:
        """Render super content with proper context."""
        return self.get_super_content(block_name)


# ================= Module Exports =================

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
