"""
Bulk Update Returning - Update records and get back updated rows

Extends bulk operations to return the updated rows, useful for:
- Verifying updates were applied correctly
- Getting new field values without a separate query
- Batch update with instant feedback

Usage:
    from eden_orm.bulk_update_returning import bulk_update_returning
    
    # Update and get back the updated records
    updated = await bulk_update_returning(
        User,
        updates={'is_active': True},
        filter_kwargs={'age__gte': 18}
    )
    # Returns list of User instances with new values
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class BulkUpdateResult:
    """Result of a bulk update operation."""
    
    updated_count: int
    updated_objects: List[Any]
    failed_ids: List[Any] = None
    
    def __post_init__(self):
        if self.failed_ids is None:
            self.failed_ids = []


class BulkUpdateReturning:
    """
    Bulk update operations that return updated records.
    """
    
    @staticmethod
    async def bulk_update_returning(
        model_class: Any,
        updates: Dict[str, Any],
        filter_kwargs: Optional[Dict[str, Any]] = None,
        batch_size: int = 1000
    ) -> BulkUpdateResult:
        """
        Update multiple records and return the updated objects.
        
        Args:
            model_class: The model class to update
            updates: Dictionary of field: value pairs to update
            filter_kwargs: WHERE conditions (e.g., {'status': 'inactive'})
            batch_size: Batch size for processing
        
        Returns:
            BulkUpdateResult with updated_count and updated_objects list
        
        Usage:
            result = await BulkUpdateReturning.bulk_update_returning(
                User,
                updates={'is_verified': True},
                filter_kwargs={'email_confirmed': True}
            )
            print(f"Updated {result.updated_count} users")
            for user in result.updated_objects:
                print(f"  - {user.email}: verified={user.is_verified}")
        """
        if not updates:
            raise ValueError("updates dict cannot be empty")
        
        table_name = model_class.__tablename__
        
        # Build WHERE clause from filter_kwargs
        where_clause = ""
        where_params = []
        param_count = 1
        
        if filter_kwargs:
            where_parts = []
            for key, value in filter_kwargs.items():
                where_parts.append(f"{key} = ${param_count}")
                where_params.append(value)
                param_count += 1
            
            where_clause = " WHERE " + " AND ".join(where_parts)
        
        # Build SET clause from updates
        set_parts = []
        for field, value in updates.items():
            set_parts.append(f"{field} = ${param_count}")
            where_params.append(value)
            param_count += 1
        
        set_clause = ", ".join(set_parts)
        
        # Build UPDATE with RETURNING * clause
        query = f"UPDATE {table_name} SET {set_clause}{where_clause} RETURNING *"
        
        updated_objects = []
        failed_ids = []
        
        try:
            if hasattr(model_class, 'db_connection') and model_class.db_connection:
                rows = await model_class.db_connection.fetch(query, *where_params)
                
                # Convert rows to model instances
                for row in rows:
                    try:
                        obj = model_class(**dict(row))
                        updated_objects.append(obj)
                    except Exception as e:
                        logger.warning(f"Failed to instantiate updated object: {e}")
                        if hasattr(row, 'id'):
                            failed_ids.append(row.id)
                
                logger.info(f"Bulk updated {len(updated_objects)} records in {table_name}")
                
                return BulkUpdateResult(
                    updated_count=len(updated_objects),
                    updated_objects=updated_objects,
                    failed_ids=failed_ids
                )
        except Exception as e:
            logger.error(f"Bulk update returning failed: {e}")
            raise
        
        return BulkUpdateResult(
            updated_count=0,
            updated_objects=[],
            failed_ids=[]
        )
    
    @staticmethod
    async def bulk_update_returning_batch(
        model_class: Any,
        update_list: List[Dict[str, Any]],
        id_field: str = 'id',
        batch_size: int = 1000
    ) -> BulkUpdateResult:
        """
        Update multiple records with individual values (true bulk update).
        
        Args:
            model_class: The model class to update
            update_list: List of dicts with id and fields to update
                        [{'id': 1, 'field': 'value'}, ...]
            id_field: Name of the ID field (default: 'id')
            batch_size: Batch size for processing
        
        Returns:
            BulkUpdateResult with total updated count
        
        Usage:
            result = await BulkUpdateReturning.bulk_update_returning_batch(
                User,
                [
                    {'id': 1, 'email': 'new1@test.com'},
                    {'id': 2, 'email': 'new2@test.com'},
                    {'id': 3, 'email': 'new3@test.com'},
                ]
            )
            print(f"Updated {result.updated_count} records")
        """
        if not update_list:
            return BulkUpdateResult(updated_count=0, updated_objects=[])
        
        table_name = model_class.__tablename__
        updated_objects = []
        failed_ids = []
        
        try:
            # Process in batches
            for i in range(0, len(update_list), batch_size):
                batch = update_list[i:i+batch_size]
                
                # Build CASE statement for batch update
                case_statements = {}
                ids_to_update = []
                
                for update_item in batch:
                    obj_id = update_item[id_field]
                    ids_to_update.append(obj_id)
                    
                    for field, value in update_item.items():
                        if field != id_field:
                            if field not in case_statements:
                                case_statements[field] = []
                            case_statements[field].append((obj_id, value))
                
                # Build UPDATE query with CASE statements
                set_clauses = []
                params = []
                param_count = 1
                
                for field, cases in case_statements.items():
                    case_sql = f"CASE"
                    for obj_id, value in cases:
                        case_sql += f" WHEN {id_field} = ${param_count} THEN ${param_count + 1}"
                        params.extend([obj_id, value])
                        param_count += 2
                    case_sql += f" ELSE {field} END"
                    set_clauses.append(f"{field} = {case_sql}")
                
                # Build WHERE clause for IDs
                id_placeholders = ", ".join([f"${param_count + i}" for i in range(len(ids_to_update))])
                params.extend(ids_to_update)
                
                query = f"UPDATE {table_name} SET {', '.join(set_clauses)} WHERE {id_field} IN ({id_placeholders}) RETURNING *"
                
                if hasattr(model_class, 'db_connection') and model_class.db_connection:
                    rows = await model_class.db_connection.fetch(query, *params)
                    
                    for row in rows:
                        try:
                            obj = model_class(**dict(row))
                            updated_objects.append(obj)
                        except Exception as e:
                            logger.warning(f"Failed to instantiate updated object: {e}")
                            if hasattr(row, id_field):
                                failed_ids.append(getattr(row, id_field))
            
            logger.info(f"Bulk batch updated {len(updated_objects)} records")
            
            return BulkUpdateResult(
                updated_count=len(updated_objects),
                updated_objects=updated_objects,
                failed_ids=failed_ids
            )
        
        except Exception as e:
            logger.error(f"Bulk batch update returning failed: {e}")
            raise
