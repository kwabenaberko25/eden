"""
Eden Admin Panel — Inline Model Rendering

Provides rendering and data preparation for inline models (related objects edited together).

Supports:
- Tabular inlines (rows in a table)
- Stacked inlines (field blocks)
- Automatic relationship detection
- Form field generation
- Data pre-population from related objects
- Deletion and addition of related records

**Usage:**

    from eden.admin.inline import prepare_inline_data, render_inline_form
    
    # In admin view:
    inline_data = await prepare_inline_data(parent_model_admin, parent_instance)
    context["inlines"] = inline_data
"""

import logging
from typing import Any, Dict, List, Optional, Type, Tuple
from sqlalchemy import inspect as sa_inspect

logger = logging.getLogger(__name__)


class InlineModelHelper:
    """Utilities for working with inline models."""
    
    @staticmethod
    def get_foreign_key_field(
        parent_model: Type,
        child_model: Type,
    ) -> Optional[str]:
        """
        Find the foreign key field in child model that references parent model.
        
        Args:
            parent_model: The parent model class
            child_model: The child/inline model class
        
        Returns:
            Name of the foreign key field, or None if not found
        
        Example:
            # SupportTicket -> TicketMessage
            fk = get_foreign_key_field(SupportTicket, TicketMessage)
            # Returns: "ticket_id"
        """
        try:
            child_mapper = sa_inspect(child_model)
            parent_tablename = getattr(parent_model, "__tablename__", parent_model.__name__.lower())
            
            # Look for FK columns matching parent table name
            for col in child_mapper.columns:
                col_name_lower = str(col.key).lower()
                
                # Check if column name matches pattern: parent_table_name + "_id"
                pattern = f"{parent_tablename.rstrip('s')}_id"
                if col_name_lower == pattern:
                    return col.key
                
                # Also check full tablename
                pattern2 = f"{parent_tablename}_id"
                if col_name_lower == pattern2:
                    return col.key
                
                # Check foreign keys directly
                if hasattr(col, "foreign_keys"):
                    for fk in col.foreign_keys:
                        if parent_tablename in str(fk.column.table):
                            return col.key
            
            return None
        except Exception as e:
            logger.error(f"Failed to find FK field: {e}")
            return None
    
    @staticmethod
    async def get_related_objects(
        parent_instance: Any,
        child_model: Type,
        fk_field_name: str,
    ) -> List[Any]:
        """
        Fetch related child objects for a parent instance.
        
        Args:
            parent_instance: Instance of the parent model
            child_model: The child/inline model class
            fk_field_name: Name of the foreign key field
        
        Returns:
            List of related instances
        """
        try:
            parent_id = getattr(parent_instance, "id", None)
            if not parent_id:
                return []
            
            # Query related objects
            related = await child_model.query().filter(**{
                fk_field_name: parent_id
            }).all()
            
            return related or []
        except Exception as e:
            logger.warning(f"Failed to fetch related objects: {e}")
            return []
    
    @staticmethod
    def get_model_fields(
        model: Type,
        exclude_fields: Optional[List[str]] = None,
    ) -> List[Tuple[str, str, Any]]:
        """
        Extract fieldnames and metadata from a model.
        
        Args:
            model: The model class
            exclude_fields: Fields to skip (e.g., "id", FK fields)
        
        Returns:
            List of (field_name, field_label, field_metadata) tuples
        """
        exclude_fields = exclude_fields or []
        fields = []
        
        try:
            mapper = sa_inspect(model)
            
            for col in mapper.columns:
                if col.key in exclude_fields:
                    continue
                
                # Get field metadata if available
                metadata = {}
                if hasattr(model, col.key):
                    attr = getattr(model, col.key)
                    if hasattr(attr, "info"):
                        metadata = attr.info
                
                label = metadata.get("label", col.key.replace("_", " ").title())
                fields.append((col.key, label, metadata))
            
            return fields
        except Exception as e:
            logger.error(f"Failed to extract fields from {model}: {e}")
            return []


async def prepare_inline_data(
    model_admin: Any,
    parent_instance: Any,
    parent_model: Type,
) -> List[Dict[str, Any]]:
    """
    Prepare data for rendering inline forms.
    
    For each inline configured in model_admin:
    1. Find FK field linking to parent
    2. Fetch related objects
    3. Extract field metadata
    4. Format for template rendering
    
    Args:
        model_admin: The ModelAdmin instance
        parent_instance: The parent model instance
        parent_model: The parent model class
    
    Returns:
        List of inline data dictionaries ready for template rendering
    
    Example:
        ticket = await SupportTicket.get(1)
        inlines = await prepare_inline_data(ticket_admin, ticket, SupportTicket)
        # Returns: [
        #   {
        #     'model_name': 'TicketMessage',
        #     'template': 'tabular_inline',
        #     'fields': [('content', 'Content'), ...],
        #     'rows': [
        #       {'id': 1, 'content': 'First message', ...},
        #       {'id': 2, 'content': 'Second message', ...},
        #       {'id': None, 'content': '', ...}  # Empty row for new
        #     ]
        #   }
        # ]
    """
    inlines_data = []
    
    if not hasattr(model_admin, "inlines"):
        return inlines_data
    
    for inline_class in model_admin.inlines:
        try:
            inline = inline_class()
            child_model = inline.model
            
            # 1. Find foreign key field
            fk_field = InlineModelHelper.get_foreign_key_field(
                parent_model,
                child_model
            )
            
            if not fk_field:
                logger.warning(
                    f"Could not find FK from {child_model.__name__} to {parent_model.__name__}"
                )
                continue
            
            # 2. Fetch related objects
            related_objects = await InlineModelHelper.get_related_objects(
                parent_instance,
                child_model,
                fk_field
            )
            
            # 3. Get field metadata
            exclude_fields = [fk_field, "id"] + getattr(inline, "exclude_fields", [])
            fields = InlineModelHelper.get_model_fields(child_model, exclude_fields)
            field_names = [f[0] for f in fields]
            
            # 4. Format rows
            rows = []
            
            # Add existing related objects
            for obj in related_objects:
                row = {
                    "id": getattr(obj, "id", None),
                    "DELETE": False,
                }
                for field_name, _, _ in fields:
                    row[field_name] = getattr(obj, field_name, "")
                rows.append(row)
            
            # Add empty rows for new objects
            extra = getattr(inline, "extra", 1)
            for _ in range(extra):
                row = {
                    "id": None,
                    "DELETE": False,
                }
                for field_name, _, _ in fields:
                    row[field_name] = ""
                rows.append(row)
            
            # 5. Build inline data
            inline_data = {
                "model_name": child_model.__name__,
                "model_label": getattr(inline, "verbose_name", child_model.__name__),
                "fk_field": fk_field,
                "template": getattr(inline, "template", "tabular_inline"),
                "extra": extra,
                "max_num": getattr(inline, "max_num", None),
                "min_num": getattr(inline, "min_num", 0),
                "fields": [
                    {
                        "name": name,
                        "label": label,
                        "metadata": metadata,
                    }
                    for name, label, metadata in fields
                ],
                "rows": rows,
            }
            
            inlines_data.append(inline_data)
        
        except Exception as e:
            logger.error(f"Failed to prepare inline data for {inline_class}: {e}", exc_info=True)
            continue
    
    return inlines_data


async def process_inline_forms(
    request_data: Dict[str, Any],
    parent_instance: Any,
    parent_model: Type,
    model_admin: Any,
) -> Dict[str, Any]:
    """
    Process inline form submissions and save related objects.
    
    Parses form data for each inline and:
    1. Creates/updates related objects
    2. Deletes marked objects
    3. Validates data
    4. Returns summary
    
    Args:
        request_data: The request form data
        parent_instance: The parent model instance
        parent_model: The parent model class
        model_admin: The ModelAdmin instance
    
    Returns:
        Dictionary with:
        - success: bool
        - message: str
        - created: int (number of new records)
        - updated: int (number of modified records)
        - deleted: int (number of deleted records)
        - errors: list (any validation errors)
    
    Example:
        form_data = await request.form()
        result = await process_inline_forms(
            form_data,
            ticket,
            SupportTicket,
            ticket_admin
        )
        if result['success']:
            # Show success message
            pass
    """
    result = {
        "success": True,
        "message": "Inline forms processed",
        "created": 0,
        "updated": 0,
        "deleted": 0,
        "errors": [],
    }
    
    if not hasattr(model_admin, "inlines"):
        return result
    
    parent_id = getattr(parent_instance, "id", None)
    if not parent_id:
        result["success"] = False
        result["message"] = "Parent instance has no ID"
        return result
    
    try:
        for inline_class in model_admin.inlines:
            inline = inline_class()
            child_model = inline.model
            
            # Find FK field
            fk_field = InlineModelHelper.get_foreign_key_field(
                parent_model,
                child_model
            )
            
            if not fk_field:
                result["errors"].append(f"FK field not found for {child_model.__name__}")
                continue
            
            # Parse inline_{model_name}_{index}_{field_name} form fields
            model_name_lower = child_model.__name__.lower()
            inline_prefix = f"inline_{child_model.__name__}_"
            
            # Group fields by index
            rows_data = {}
            for key, value in request_data.items():
                if not key.startswith(inline_prefix):
                    continue
                
                parts = key.split("_")
                if len(parts) < 4:
                    continue
                
                # Format: inline_{ModelName}_{index}_{field_name}
                try:
                    index = int(parts[3])
                    field_name = "_".join(parts[4:])
                except (ValueError, IndexError):
                    continue
                
                if index not in rows_data:
                    rows_data[index] = {}
                rows_data[index][field_name] = value
            
            # Process each row
            for index, row_data in sorted(rows_data.items()):
                # Check if marked for deletion
                if row_data.get("DELETE") in ("on", "true", "1", True):
                    obj_id = row_data.get("id")
                    if obj_id:
                        try:
                            obj = await child_model.get(id=obj_id)
                            if obj:
                                await obj.delete()
                                result["deleted"] += 1
                        except Exception as e:
                            result["errors"].append(f"Failed to delete record {obj_id}: {e}")
                    continue
                
                # Skip empty rows
                has_data = any(
                    v for k, v in row_data.items()
                    if k not in ("id", "DELETE")
                )
                if not has_data:
                    continue
                
                # Create or update
                obj_id = row_data.get("id")
                if obj_id:
                    # Update existing
                    try:
                        obj = await child_model.get(id=obj_id)
                        if not obj:
                            result["errors"].append(f"Record {obj_id} not found")
                            continue
                        
                        for field_name, value in row_data.items():
                            if field_name not in ("id", "DELETE"):
                                setattr(obj, field_name, value)
                        
                        await obj.save()
                        result["updated"] += 1
                    except Exception as e:
                        result["errors"].append(f"Failed to update record {obj_id}: {e}")
                else:
                    # Create new
                    try:
                        obj = child_model()
                        setattr(obj, fk_field, parent_id)
                        
                        for field_name, value in row_data.items():
                            if field_name not in ("id", "DELETE"):
                                setattr(obj, field_name, value)
                        
                        await obj.save()
                        result["created"] += 1
                    except Exception as e:
                        result["errors"].append(f"Failed to create record: {e}")
        
        if result["errors"]:
            result["success"] = False
            result["message"] = f"Processed with {len(result['errors'])} error(s)"
        
        return result
    
    except Exception as e:
        logger.error(f"Error processing inline forms: {e}", exc_info=True)
        result["success"] = False
        result["message"] = str(e)
        return result
