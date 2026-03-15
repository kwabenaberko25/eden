"""
Eden — Slug Field Auto-Generation Mixin

Provides automatic slug generation from source fields.

**Features:**
- Auto-generate slugs from any field (title, name, etc.)
- Unique slug handling (appends -1, -2, etc. for duplicates)
- Preserves manual slug overrides
- Slugification customization

**Usage:**

    from eden.db import Model, StringField, SlugField, SlugMixin
    
    class Post(Model, SlugMixin):
        title: Mapped[str] = StringField(required=True)
        slug: Mapped[str] = SlugField(populate_from="title")
        
        # Auto-config: slug auto-generates from title before save
    
    post = await Post.create(title="Hello World")
    print(post.slug)  # Output: "hello-world"
    
    # Manual override still works
    post2 = await Post.create(title="Hello World", slug="custom-slug")
    print(post2.slug)  # Output: "custom-slug"
"""

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


def slugify(text: str, max_length: int = 255) -> str:
    """
    Convert any text to a URL-friendly slug.
    
    Args:
        text: Text to slugify
        max_length: Maximum slug length
    
    Returns:
        URL-friendly slug
    
    Example:
        slugify("Hello World!")  # Returns: "hello-world"
        slugify("Special @#$ Chars")  # Returns: "special-chars"
    """
    # Convert to lowercase
    text = text.lower()
    
    # Replace spaces and underscores with hyphens
    text = re.sub(r'[\s_]+', '-', text)
    
    # Remove all characters except alphanumeric and hyphens
    text = re.sub(r'[^a-z0-9-]', '', text)
    
    # Replace multiple consecutive hyphens with single hyphen
    text = re.sub(r'-+', '-', text)
    
    # Remove leading/trailing hyphens
    text = text.strip('-')
    
    # Truncate to max length
    if len(text) > max_length:
        text = text[:max_length].rstrip('-')
    
    return text


class SlugMixin:
    """
    Mixin to add automatic slug generation to models.
    
    When a model has a SlugField with `populate_from` set, this mixin will
    automatically generate the slug from the source field before saving.
    
    Example:
        class Article(Model, SlugMixin):
            title: Mapped[str] = StringField()
            slug: Mapped[str] = SlugField(populate_from="title")
        
        article = Article(title="My Article")
        await article.save()  # slug auto-set to "my-article"
    """
    
    async def _generate_slugs(self) -> None:
        """
        Auto-generate slugs for all SlugFields with populate_from.
        Called automatically by save() and create().
        """
        from sqlalchemy.orm import DeclarativeBase
        from sqlalchemy.inspection import inspect as sa_inspect
        
        # Get model class (handle proxy classes)
        model_class = self.__class__
        
        # Inspect mapped columns
        mapper = sa_inspect(model_class)
        if mapper is None:
            return
        
        for column in mapper.columns:
            # Check if column has populate_from info
            column_info = column.info or {}
            populate_from = column_info.get("populate_from")
            
            if not populate_from:
                continue
            
            # Get the current slug value
            slug_value = getattr(self, column.name, None)
            
            # Skip if slug is already manually set (non-empty)
            if slug_value and isinstance(slug_value, str) and slug_value.strip():
                continue
            
            # Get source field value
            source_value = getattr(self, populate_from, None)
            if not source_value:
                continue
            
            # Generate slug from source
            generated_slug = slugify(str(source_value), max_length=column.type.length or 255)
            setattr(self, column.name, generated_slug)
            
            logger.debug(f"Auto-generated slug: {column.name}={generated_slug} (from {populate_from}={source_value})")
    
    async def _ensure_unique_slug(self) -> None:
        """
        Ensure slug uniqueness by appending numeric suffix if needed.
        Called after _generate_slugs() during save.
        """
        from sqlalchemy.orm import DeclarativeBase
        from sqlalchemy.inspection import inspect as sa_inspect
        
        model_class = self.__class__
        mapper = sa_inspect(model_class)
        if mapper is None:
            return
        
        for column in mapper.columns:
            # Only process unique slug fields
            if not column.unique or not column.info or "populate_from" not in column.info:
                continue
            
            slug_value = getattr(self, column.name, None)
            if not slug_value:
                continue
            
            # Check if this slug already exists in database (excluding self)
            from .query import QuerySet
            
            existing = await QuerySet(model_class).filter(**{column.name: slug_value}).first()
            
            if existing and existing != self:
                # Slug exists, try appending numeric suffix
                counter = 1
                base_slug = slug_value
                
                while existing:
                    new_slug = f"{base_slug}-{counter}"
                    existing = await QuerySet(model_class).filter(**{column.name: new_slug}).first()
                    counter += 1
                
                setattr(self, column.name, new_slug)
                logger.debug(f"Slug collision resolved: {column.name}={new_slug}")
    
    async def save(self, *args, **kwargs):
        """Override save to auto-generate slugs before saving."""
        # Auto-generate slugs
        await self._generate_slugs()
        
        # Ensure uniqueness if needed
        await self._ensure_unique_slug()
        
        # Call parent save
        return await super().save(*args, **kwargs)


def auto_slugify_field(field_name: str = "slug", source_field: str = "title"):
    """
    Decorator/helper to configure auto-slug generation for a model.
    
    Alternative to SlugMixin for models that can't use multiple inheritance.
    
    Args:
        field_name: Name of the slug field (default: "slug")
        source_field: Name of the source field to slugify from (default: "title")
    
    Example:
        @auto_slugify_field(field_name="slug", source_field="title")
        class Article(Model):
            title: Mapped[str] = StringField()
            slug: Mapped[str] = SlugField()
    """
    def decorator(cls):
        # Store slug config in class
        if not hasattr(cls, "_slug_config"):
            cls._slug_config = {}
        
        cls._slug_config[field_name] = source_field
        return cls
    
    return decorator
