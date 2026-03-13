"""
Aggregation Functions - COUNT, SUM, AVG, MIN, MAX on querysets

Allows computing aggregate values across groups of records:
- count() - Count records
- sum(field) - Sum numeric field values  
- avg(field) - Average of numeric field
- min(field) - Minimum value
- max(field) - Maximum value
- group_by(*fields) - Group results by field(s)

Usage:
    # Count total users
    total = await User.objects.count()
    
    # Sum of all purchase amounts
    total_spent = await Purchase.objects.aggregate('amount')
    
    # Average order value
    avg_order = await Order.objects.avg('total')
    
    # Group and aggregate
    result = await Order.objects.group_by('status').aggregate('total', func='sum')
    # Returns: [{'status': 'pending', 'total_sum': 1000}, {'status': 'complete', 'total_sum': 5000}]
"""

from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class AggregateFunction(Enum):
    """Supported aggregate functions."""
    COUNT = "COUNT"
    SUM = "SUM"
    AVG = "AVG"
    MIN = "MIN"
    MAX = "MAX"


@dataclass
class AggregateResult:
    """Result of an aggregate query."""
    
    function: str
    field: str
    group_by: Optional[List[str]] = None
    result: Union[int, float, List[Dict[str, Any]]] = None


class Aggregation:
    """Aggregation query builder and executor."""
    
    @staticmethod
    async def count(
        model_class: Any,
        filter_kwargs: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Count records matching criteria.
        
        Args:
            model_class: The model class to count
            filter_kwargs: Optional WHERE conditions
        
        Returns:
            Number of matching records
        
        Usage:
            active_users = await Aggregation.count(User, {'is_active': True})
        """
        from .connection import get_session
        
        table_name = model_class.__tablename__
        
        query = f"SELECT COUNT(*) as count FROM {table_name}"
        where_clause = ""
        params = []
        
        if filter_kwargs:
            conditions = []
            for i, (key, value) in enumerate(filter_kwargs.items(), 1):
                conditions.append(f"{key} = ${i}")
                params.append(value)
            where_clause = " WHERE " + " AND ".join(conditions)
        
        query += where_clause
        
        try:
            async with await get_session() as session:
                result = await session.fetchval(query, *params)
                return int(result) if result else 0
        except Exception as e:
            logger.error(f"Count query failed: {e}")
            raise
    
    @staticmethod
    async def sum(
        model_class: Any,
        field_name: str,
        filter_kwargs: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        Sum values of a numeric field.
        
        Args:
            model_class: The model class
            field_name: Field to sum
            filter_kwargs: Optional WHERE conditions
        
        Returns:
            Sum of field values
        
        Usage:
            total = await Aggregation.sum(Order, 'amount', {'status': 'complete'})
        """
        from .connection import get_session
        
        table_name = model_class.__tablename__
        
        query = f"SELECT SUM({field_name}) as total FROM {table_name}"
        where_clause = ""
        params = []
        
        if filter_kwargs:
            conditions = []
            for i, (key, value) in enumerate(filter_kwargs.items(), 1):
                conditions.append(f"{key} = ${i}")
                params.append(value)
            where_clause = " WHERE " + " AND ".join(conditions)
        
        query += where_clause
        
        try:
            async with await get_session() as session:
                result = await session.fetchval(query, *params)
                return float(result) if result else 0.0
        except Exception as e:
            logger.error(f"Sum query failed: {e}")
            raise
    
    @staticmethod
    async def avg(
        model_class: Any,
        field_name: str,
        filter_kwargs: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        Calculate average of a numeric field.
        
        Args:
            model_class: The model class
            field_name: Field to average
            filter_kwargs: Optional WHERE conditions
        
        Returns:
            Average value
        
        Usage:
            avg_price = await Aggregation.avg(Product, 'price', {'category': 'books'})
        """
        from .connection import get_session
        
        table_name = model_class.__tablename__
        
        query = f"SELECT AVG({field_name}) as average FROM {table_name}"
        where_clause = ""
        params = []
        
        if filter_kwargs:
            conditions = []
            for i, (key, value) in enumerate(filter_kwargs.items(), 1):
                conditions.append(f"{key} = ${i}")
                params.append(value)
            where_clause = " WHERE " + " AND ".join(conditions)
        
        query += where_clause
        
        try:
            async with await get_session() as session:
                result = await session.fetchval(query, *params)
                return float(result) if result else 0.0
        except Exception as e:
            logger.error(f"Average query failed: {e}")
            raise
    
    @staticmethod
    async def min(
        model_class: Any,
        field_name: str,
        filter_kwargs: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Get minimum value of a field.
        
        Args:
            model_class: The model class
            field_name: Field to find minimum
            filter_kwargs: Optional WHERE conditions
        
        Returns:
            Minimum value
        """
        from .connection import get_session
        
        table_name = model_class.__tablename__
        
        query = f"SELECT MIN({field_name}) as minimum FROM {table_name}"
        where_clause = ""
        params = []
        
        if filter_kwargs:
            conditions = []
            for i, (key, value) in enumerate(filter_kwargs.items(), 1):
                conditions.append(f"{key} = ${i}")
                params.append(value)
            where_clause = " WHERE " + " AND ".join(conditions)
        
        query += where_clause
        
        try:
            async with await get_session() as session:
                result = await session.fetchval(query, *params)
                return result
        except Exception as e:
            logger.error(f"Min query failed: {e}")
            raise
    
    @staticmethod
    async def max(
        model_class: Any,
        field_name: str,
        filter_kwargs: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Get maximum value of a field.
        
        Args:
            model_class: The model class
            field_name: Field to find maximum
            filter_kwargs: Optional WHERE conditions
        
        Returns:
            Maximum value
        """
        from .connection import get_session
        
        table_name = model_class.__tablename__
        
        query = f"SELECT MAX({field_name}) as maximum FROM {table_name}"
        where_clause = ""
        params = []
        
        if filter_kwargs:
            conditions = []
            for i, (key, value) in enumerate(filter_kwargs.items(), 1):
                conditions.append(f"{key} = ${i}")
                params.append(value)
            where_clause = " WHERE " + " AND ".join(conditions)
        
        query += where_clause
        
        try:
            async with await get_session() as session:
                result = await session.fetchval(query, *params)
                return result
        except Exception as e:
            logger.error(f"Max query failed: {e}")
            raise
    
    @staticmethod
    async def group_by_aggregate(
        model_class: Any,
        group_fields: List[str],
        aggregate_field: str,
        aggregate_func: str = "COUNT",
        filter_kwargs: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Group records and apply aggregate function.
        
        Args:
            model_class: The model class
            group_fields: Fields to group by
            aggregate_field: Field to aggregate (e.g., 'amount')
            aggregate_func: Aggregate function name (COUNT, SUM, AVG, MIN, MAX)
            filter_kwargs: Optional WHERE conditions
        
        Returns:
            List of dicts with grouping fields and aggregate result
        
        Usage:
            results = await Aggregation.group_by_aggregate(
                Order,
                group_fields=['status'],
                aggregate_field='amount',
                aggregate_func='SUM'
            )
            # Returns: [
            #   {'status': 'pending', 'amount_sum': 1000},
            #   {'status': 'complete', 'amount_sum': 5000}
            # ]
        """
        if aggregate_func not in [f.value for f in AggregateFunction]:
            raise ValueError(f"Invalid aggregate function: {aggregate_func}")
        
        table_name = model_class.__tablename__
        group_by_clause = ", ".join(group_fields)
        result_field = f"{aggregate_field}_{aggregate_func.lower()}"
        
        query = f"SELECT {group_by_clause}, {aggregate_func}({aggregate_field}) as {result_field} FROM {table_name}"
        
        where_clause = ""
        params = []
        
        if filter_kwargs:
            conditions = []
            for i, (key, value) in enumerate(filter_kwargs.items(), 1):
                conditions.append(f"{key} = ${i}")
                params.append(value)
            where_clause = " WHERE " + " AND ".join(conditions)
        
        query += where_clause + f" GROUP BY {group_by_clause}"
        
        from .connection import get_session
        
        try:
            async with await get_session() as session:
                rows = await session.fetch(query, *params)
                results = []
                for row in rows:
                    results.append(dict(row))
                return results
        except Exception as e:
            logger.error(f"Group by aggregate query failed: {e}")
            raise
