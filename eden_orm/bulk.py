"""
Eden ORM - Bulk Operations

Efficient batch create, update, and delete operations.
"""

import logging
from typing import List, Dict, Any, Type, Optional
from .connection import get_session

logger = logging.getLogger(__name__)


class BulkOperations:
    """Handle bulk create, update, delete operations."""
    
    @staticmethod
    async def bulk_create(
        model_class: Type,
        objects: List[Any],
        batch_size: int = 1000
    ) -> List[Any]:
        """
        Bulk create multiple objects.
        
        Args:
            model_class: Model class to create
            objects: List of model instances or dicts
            batch_size: Insert batch size
        
        Returns:
            List of created instances
        """
        if not objects:
            return []
        
        table = model_class.__tablename__
        created = []
        
        async with await get_session() as session:
            # Process in batches
            for i in range(0, len(objects), batch_size):
                batch = objects[i:i + batch_size]
                
                # Extract field names and values
                if isinstance(batch[0], dict):
                    records = batch
                else:
                    records = [
                        {k: getattr(obj, k) for k in vars(obj).keys() if not k.startswith('_')}
                        for obj in batch
                    ]
                
                if not records:
                    continue
                
                # Get field names from first record
                field_names = list(records[0].keys())
                
                # Build placeholders with correct parameter indices
                # Each row needs unique parameter indices: ($1, $2), ($3, $4), etc.
                placeholders = []
                flattened_values = []
                param_index = 1
                
                for record in records:
                    row_placeholders = []
                    for field_name in field_names:
                        row_placeholders.append(f"${param_index}")
                        flattened_values.append(record[field_name])
                        param_index += 1
                    placeholders.append(f"({', '.join(row_placeholders)})")
                
                # Build INSERT query
                sql = f"""
                INSERT INTO {table} ({', '.join(field_names)})
                VALUES {', '.join(placeholders)}
                RETURNING *
                """
                
                try:
                    rows = await session.fetch(sql, *flattened_values)
                    
                    for row in rows:
                        obj = model_class(**dict(row))
                        created.append(obj)
                        
                    logger.info(f"Bulk created {len(records)} {model_class.__tablename__} records")
                except Exception as e:
                    logger.error(f"Bulk create failed: {e}")
                    raise
        
        return created
    
    @staticmethod
    async def bulk_update(
        model_class: Type,
        updates: Dict[str, Any],
        filter_kwargs: Dict[str, Any],
        returning: bool = False
    ) -> int:
        """
        Bulk update multiple records.
        
        Args:
            model_class: Model class
            updates: Dict of fields to update
            filter_kwargs: Filter conditions (and only)
            returning: Return updated records
        
        Returns:
            Count of updated records
        """
        if not updates or not filter_kwargs:
            return 0
        
        table = model_class.__tablename__
        
        async with await get_session() as session:
            # Build SET clause
            set_clauses = [f"{k} = ${i+1}" for i, k in enumerate(updates.keys())]
            set_sql = ", ".join(set_clauses)
            
            # Build WHERE clause
            where_clauses = [f"{k} = ${len(updates)+i+1}" for i, k in enumerate(filter_kwargs.keys())]
            where_sql = " AND ".join(where_clauses)
            
            values = list(updates.values()) + list(filter_kwargs.values())
            
            returning_sql = "RETURNING *" if returning else ""
            sql = f"""
            UPDATE {table}
            SET {set_sql}
            WHERE {where_sql}
            {returning_sql}
            """
            
            try:
                if returning:
                    rows = await session.fetch(sql, *values)
                    logger.info(f"Bulk updated {len(rows)} {table} records")
                    return rows
                else:
                    result = await session.execute(sql, *values)
                    # Parse result for row count
                    result_str = str(result)
                    if "UPDATE" in result_str:
                        count = int(result_str.split()[-1]) if result_str.split()[-1].isdigit() else len(values)
                        logger.info(f"Bulk updated {count} {table} records")
                        return count
                    return 0
            except Exception as e:
                logger.error(f"Bulk update failed: {e}")
                raise
    
    @staticmethod
    async def bulk_delete(
        model_class: Type,
        filter_kwargs: Dict[str, Any]
    ) -> int:
        """
        Bulk delete multiple records.
        
        Args:
            model_class: Model class
            filter_kwargs: Filter conditions
        
        Returns:
            Count of deleted records
        """
        if not filter_kwargs:
            return 0
        
        table = model_class.__tablename__
        
        async with await get_session() as session:
            # Build WHERE clause
            where_clauses = [f"{k} = ${i+1}" for i, k in enumerate(filter_kwargs.keys())]
            where_sql = " AND ".join(where_clauses)
            
            values = list(filter_kwargs.values())
            
            sql = f"DELETE FROM {table} WHERE {where_sql}"
            
            try:
                result = await session.execute(sql, *values)
                result_str = str(result)
                if "DELETE" in result_str:
                    count = int(result_str.split()[-1]) if result_str.split()[-1].isdigit() else len(values)
                    logger.info(f"Bulk deleted {count} {table} records")
                    return count
                return 0
            except Exception as e:
                logger.error(f"Bulk delete failed: {e}")
                raise



