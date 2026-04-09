"""
Eden Component System — Template Loaders

Provides configurable template discovery and loading for components.

Supports:
- Built-in component templates (shipped with Eden)
- Project template directory overrides
- Custom theme/variant directories
- Template not-found error handling
- Debug-mode template introspection

**Usage:**

    from eden.components.loaders import ComponentTemplateLoader
    
    # Configure loader in app
    loader = ComponentTemplateLoader(
        app,
        builtin_dir="path/to/eden/components/templates",
        project_dirs=["templates/components", "templates"],
        theme="dark"
    )
    
    template = await loader.get_template("card.html")
    template = await loader.get_template("buttons/primary.html", component="button")

**Search Order:**
1. Project template directories (project_dirs)
2. Theme-specific directories (if configured)
3. Built-in component templates
"""

import os
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class BaseTemplateLoader(ABC):
    """Abstract base class for component template loaders."""
    
    @abstractmethod
    async def get_template(self, path: str) -> Optional[str]:
        """
        Load template content by path.
        
        Args:
            path: Relative path to template (e.g., "card.html")
        
        Returns:
            Template content as string, or None if not found
        """
        pass
    
    @abstractmethod
    async def template_exists(self, path: str) -> bool:
        """
        Check if a template exists without loading it.
        
        Args:
            path: Relative path to template
        
        Returns:
            True if template exists
        """
        pass
    
    @abstractmethod
    async def list_templates(self, pattern: Optional[str] = None) -> List[str]:
        """
        List available templates matching optional pattern.
        
        Args:
            pattern: Glob pattern (e.g., "**/button*.html")
        
        Returns:
            List of template paths
        """
        pass


class FileSystemTemplateLoader(BaseTemplateLoader):
    """Load templates from the file system."""
    
    def __init__(self, directories: List[str]):
        """
        Initialize filesystem loader.
        
        Args:
            directories: List of directories to search, in priority order
        """
        self.directories = [Path(d) for d in directories if d]
    
    async def get_template(self, path: str) -> Optional[str]:
        """Load template from first matching directory."""
        for directory in self.directories:
            file_path = directory / path
            if file_path.exists() and file_path.is_file():
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        logger.debug(f"Loaded template: {file_path}")
                        return f.read()
                except IOError as e:
                    logger.warning(f"Failed to read template {file_path}: {e}")
        
        logger.debug(f"Template not found in any directory: {path}")
        return None
    
    async def template_exists(self, path: str) -> bool:
        """Check if template exists in any directory."""
        for directory in self.directories:
            file_path = directory / path
            if file_path.exists() and file_path.is_file():
                return True
        return False
    
    async def list_templates(self, pattern: Optional[str] = None) -> List[str]:
        """List templates matching pattern."""
        import glob as glob_module
        templates = []
        pattern = pattern or "**/*.html"
        
        for directory in self.directories:
            if not directory.exists():
                continue
            search_path = str(directory / pattern)
            matches = glob_module.glob(search_path, recursive=True)
            for match in matches:
                rel_path = str(Path(match).relative_to(directory))
                if rel_path not in templates:
                    templates.append(rel_path)
        
        return sorted(templates)


class ComponentTemplateLoader(BaseTemplateLoader):
    """
    Smart component template loader with multi-directory support.
    
    Searches in order:
    1. Project override directories
    2. Theme-specific directories
    3. Built-in component templates
    """
    
    def __init__(
        self,
        project_dirs: Optional[List[str]] = None,
        builtin_dir: Optional[str] = None,
        theme: Optional[str] = None,
        debug: bool = False,
    ):
        """
        Initialize component template loader.
        
        Args:
            project_dirs: List of project template directories to check first
            builtin_dir: Path to built-in component templates (ships with Eden)
            theme: Optional theme name (e.g., "dark", "light")
            debug: If True, log template search paths
        """
        self.project_dirs = project_dirs or []
        self.builtin_dir = builtin_dir or self._get_default_builtin_dir()
        self.theme = theme
        self.debug = debug
        
        # Build search order
        search_dirs = []
        
        # 1. Theme-specific project directories
        if theme:
            search_dirs.extend([
                os.path.join(d, "themes", theme)
                for d in self.project_dirs
            ])
        
        # 2. Regular project directories
        search_dirs.extend(self.project_dirs)
        
        # 3. Theme-specific built-in directory
        if theme and self.builtin_dir:
            search_dirs.append(os.path.join(self.builtin_dir, "themes", theme))
        
        # 4. Built-in directory
        if self.builtin_dir:
            search_dirs.append(self.builtin_dir)
        
        self.loader = FileSystemTemplateLoader(search_dirs)
        
        if self.debug:
            logger.info(f"Component template search order: {search_dirs}")
    
    def _get_default_builtin_dir(self) -> str:
        """Get path to built-in component templates."""
        return os.path.join(
            os.path.dirname(__file__),
            "templates"
        )
    
    async def get_template(self, path: str) -> Optional[str]:
        """
        Load a component template.
        
        Args:
            path: Template path (e.g., "card.html", "buttons/primary.html")
        
        Returns:
            Template content or None if not found
        """
        if self.debug:
            logger.debug(f"Looking for template: {path}")
        
        content = await self.loader.get_template(path)
        
        if content is None:
            logger.warning(f"Template not found: {path}")
            if self.debug:
                logger.debug(f"Searched in: {[str(d) for d in self.loader.directories]}")
        
        return content
    
    async def template_exists(self, path: str) -> bool:
        """Check if template exists."""
        return await self.loader.template_exists(path)
    
    async def list_templates(self, pattern: Optional[str] = None) -> List[str]:
        """List available templates."""
        return await self.loader.list_templates(pattern)
    
    async def get_component_template(
        self,
        component_name: str,
        template_name: Optional[str] = None,
    ) -> Optional[str]:
        """
        Load template for a specific component with fallback logic.
        
        Args:
            component_name: Name of the component (e.g., "card")
            template_name: Explicit template path. If None, uses default convention.
        
        Returns:
            Template content or None if not found
        
        Example:
            # Uses default: components/card.html or eden/card.html
            template = await loader.get_component_template("card")
            
            # Uses explicit path
            template = await loader.get_component_template(
                "card",
                "my_card_template.html"
            )
        """
        if template_name:
            # Explicit template provided
            return await self.get_template(template_name)
        
        # Try convention paths:
        # 1. components/{component_name}.html
        # 2. eden/{component_name}.html
        convention_paths = [
            f"components/{component_name}.html",
            f"eden/{component_name}.html",
            f"{component_name}.html",
        ]
        
        for path in convention_paths:
            content = await self.get_template(path)
            if content:
                if self.debug:
                    logger.debug(f"Found template for {component_name}: {path}")
                return content
        
        if self.debug:
            logger.debug(f"No template found for component: {component_name}")
        return None
    
    def set_theme(self, theme: str) -> None:
        """
        Change the active theme.
        
        Args:
            theme: Theme name (e.g., "dark", "light")
        """
        self.theme = theme
        # Rebuild loader with new theme
        search_dirs = []
        
        if theme:
            search_dirs.extend([
                os.path.join(d, "themes", theme)
                for d in self.project_dirs
            ])
        
        search_dirs.extend(self.project_dirs)
        
        if theme and self.builtin_dir:
            search_dirs.append(os.path.join(self.builtin_dir, "themes", theme))
        
        if self.builtin_dir:
            search_dirs.append(self.builtin_dir)
        
        self.loader = FileSystemTemplateLoader(search_dirs)
        
        if self.debug:
            logger.info(f"Updated component template search order: {search_dirs}")


class CachedTemplateLoader(ComponentTemplateLoader):
    """
    Template loader with in-memory caching.
    
    Caches loaded templates to avoid repeated file I/O.
    Useful in production for performance.
    """
    
    def __init__(self, *args, **kwargs):
        """Initialize with cache."""
        super().__init__(*args, **kwargs)
        self._cache: Dict[str, Optional[str]] = {}
        self._cache_enabled = True
    
    async def get_template(self, path: str) -> Optional[str]:
        """Get template with caching."""
        if path in self._cache:
            if self.debug:
                logger.debug(f"Cache hit: {path}")
            return self._cache[path]
        
        content = await super().get_template(path)
        
        if self._cache_enabled:
            self._cache[path] = content
        
        return content
    
    def clear_cache(self) -> None:
        """Clear template cache."""
        self._cache.clear()
        logger.info("Template cache cleared")
    
    def set_cache_enabled(self, enabled: bool) -> None:
        """Enable/disable caching."""
        self._cache_enabled = enabled
        if not enabled:
            self.clear_cache()
