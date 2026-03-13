"""
Eden ORM - Nested Prefetch Caching

Supports recursive prefetch_related with dot notation for nested relationships.
Example: prefetch_related("author", "comments__author")
"""

from typing import Any, Dict, List, Optional, Type, Set
import logging

logger = logging.getLogger(__name__)


class NestedPrefetchDescriptor:
    """Manages nested relationship fetching with caching."""
    
    def __init__(self):
        self.prefetch_cache: Dict[str, Dict[Any, Any]] = {}
    
    async def resolve_nested_path(
        self,
        model_class: Type,
        path: str,
        instance_ids: List[Any]
    ) -> Dict[Any, List[Any]]:
        """
        Resolve a nested relationship path.
        
        Example: "comments__author" from Post
        1. Load comments where post_id IN (post_ids)
        2. Get author_ids from comments
        3. Load authors where id IN (author_ids)
        4. Return nested structure
        
        Args:
            model_class: Starting model class (e.g., Post)
            path: Dot-separated path (e.g., "comments__author")
            instance_ids: List of starting instance IDs
            
        Returns:
            Dict mapping parent IDs to lists of related objects
        """
        parts = path.split("__")
        
        # Start with the initial model and IDs
        current_model = model_class
        current_ids = instance_ids
        cache_key = f"{model_class.__name__}:{path}"
        
        # Cache hit
        if cache_key in self.prefetch_cache:
            return self.prefetch_cache[cache_key]
        
        results = {}
        
        # First level relationship
        first_rel = parts[0]
        fk_field_name = f"{first_rel}_id"
        
        # Special handling for reverse relationships (e.g., comments from post)
        if first_rel + "s" in dir(model_class):
            # This is a reverse relationship like post.comments
            related_model_name = first_rel.capitalize()
            
            # Try to find the model by traversing through relationships
            from .relationships import get_model_from_string
            related_model = await self._get_related_model(model_class, first_rel)
            
            if related_model:
                # Query: SELECT * FROM comments WHERE post_id IN (...)
                session = await __import__('eden_orm.connection', fromlist=['get_session']).get_session()
                rows = await session.fetch(
                    f"SELECT * FROM {related_model.__tablename__} WHERE {model_class.__tablename__[:-1]}_id = ANY($1)",
                    current_ids
                )
                
                # Group by parent ID
                results_by_parent = {}
                for row in rows:
                    parent_id = row[f"{model_class.__tablename__[:-1]}_id"]
                    if parent_id not in results_by_parent:
                        results_by_parent[parent_id] = []
                    
                    # Convert row to model instance
                    instance = related_model()
                    for field_name in related_model.__fields__:
                        if field_name in row:
                            setattr(instance, field_name, row[field_name])
                    results_by_parent[parent_id].append(instance)
                
                results = results_by_parent
                current_ids = [row["id"] for row in rows]
                current_model = related_model
        
        # Handle nested levels (if any)
        if len(parts) > 1:
            nested_path = "__".join(parts[1:])
            
            # Get all IDs from first level
            all_nested_ids = []
            for nested_instances in results.values():
                for instance in nested_instances:
                    if hasattr(instance, f"{parts[1]}_id"):
                        nested_id = getattr(instance, f"{parts[1]}_id")
                        if nested_id:
                            all_nested_ids.append(nested_id)
            
            # Recursively resolve nested path
            nested_results = await self.resolve_nested_path(current_model, nested_path, list(set(all_nested_ids)))
            
            # Attach nested results to parent instances
            for parent_id, parent_instances in results.items():
                for instance in parent_instances:
                    for nested_id, nested_objs in nested_results.items():
                        if getattr(instance, f"{parts[1]}_id", None) == nested_id:
                            setattr(instance, f"_nested_{nested_path}", nested_objs)
        
        # Cache result
        self.prefetch_cache[cache_key] = results
        
        return results
    
    async def _get_related_model(self, model_class: Type, relation_name: str) -> Optional[Type]:
        """Infer related model from relationship name."""
        # Try to find the model by checking ForeignKeyField relationships
        # This is more reliable than string matching
        
        for field_name in dir(model_class):
            field = getattr(model_class, field_name, None)
            
            # Check if this field matches the relation name
            if hasattr(field, '__class__') and field.__class__.__name__ == 'ForeignKeyField':
                if field_name == relation_name or field_name == f"{relation_name}_id":
                    # Get the target model
                    if hasattr(field, 'to_model') and field.to_model:
                        return field.to_model
        
        # Alternative: if the relation ends with 's', check for reverse relationships
        # by looking for a foreign key that references this model
        singular = relation_name.rstrip('s')
        
        for field_name in dir(model_class):
            field = getattr(model_class, field_name, None)
            
            # Look for fields that reference this model
            if hasattr(field, '__class__') and field.__class__.__name__ == 'ForeignKeyField':
                if hasattr(field, 'to_model') and field.to_model:
                    # Check if the table name suggests it relates to the desired relation
                    if hasattr(field.to_model, '__tablename__'):
                        if field.to_model.__tablename__.rstrip('s') == singular:
                            return field.to_model
        
        return None
    
    def clear_cache(self):
        """Clear prefetch cache."""
        self.prefetch_cache.clear()


class NestedPrefetchQuerySet:
    """Extended QuerySet with nested prefetch support."""
    
    def __init__(self, query_chain):
        self.query_chain = query_chain
        self.prefetcher = NestedPrefetchDescriptor()
        self.nested_prefetch_fields: List[str] = []
    
    async def prefetch_nested(self, *paths: str) -> "NestedPrefetchQuerySet":
        """
        Add nested prefetch relationships.
        
        Usage:
            posts = await Post.prefetch_nested("author", "comments__author").all()
        
        Args:
            paths: Relationship paths, supporting dot notation for nesting
        """
        self.nested_prefetch_fields.extend(paths)
        return self
    
    async def all_nested(self):
        """Execute query with nested prefetch."""
        # First, execute normal query
        base_results = await self.query_chain.all()
        
        if not base_results or not self.nested_prefetch_fields:
            return base_results
        
        # Get IDs of base results
        model_class = self.query_chain.model_class
        base_ids = [getattr(obj, model_class.__primary_key__) for obj in base_results]
        
        # For each nested prefetch path, fetch and attach
        for path in self.nested_prefetch_fields:
            nested_results = await self.prefetcher.resolve_nested_path(
                model_class,
                path,
                base_ids
            )
            
            # Attach nested results to base objects
            for base_obj in base_results:
                obj_id = getattr(base_obj, model_class.__primary_key__)
                if obj_id in nested_results:
                    setattr(base_obj, f"_prefetch_{path}", nested_results[obj_id])
        
        return base_results
