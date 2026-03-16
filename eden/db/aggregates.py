"""
Eden — Database Aggregates

Django-style aggregation functions that wrap SQLAlchemy's func calls.
These allow for expressive data analysis in QuerySet.aggregate() and QuerySet.annotate().
"""

from __future__ import annotations

import operator
from collections.abc import Callable
from typing import Any

from sqlalchemy import func


class Aggregate:
    """
    Base class for aggregation functions.
    Supports arithmetic operations with other aggregates or numbers.
    """

    function: str = ""

    def __init__(self, field: str, alias: str | None = None) -> None:
        self.field = field
        self.alias = alias

    def resolve(self, model: type[Any], columns: Any = None) -> Any:
        if columns is not None:
            # Try to find the column in the provided columns (e.g., subquery.c)
            column = getattr(columns, self.field, None)
            if column is None:
                # Fallback: check for column name in mapper info if attribute name not found
                from sqlalchemy import inspect as sa_inspect
                mapper = sa_inspect(model)
                if self.field in mapper.all_orm_descriptors:
                    desc = mapper.all_orm_descriptors[self.field]
                    if hasattr(desc, "property") and hasattr(desc.property, "columns"):
                        col_name = desc.property.columns[0].name
                        column = getattr(columns, col_name, None)
        else:
            column = getattr(model, self.field, None)

        if column is None:
            # Final fallback: check for column name in mapper
            from sqlalchemy import inspect as sa_inspect
            mapper = sa_inspect(model)
            if self.field in mapper.columns:
                column = mapper.columns[self.field]
            else:
                raise ValueError(f"'{model.__name__}' has no field '{self.field}'")

        agg_func = getattr(func, self.function.lower())
        expr = agg_func(column)

        if self.alias:
            return expr.label(self.alias)
        return expr.label(f"{self.field}__{self.function.lower()}")

    # Arithmetic operators for combining aggregates (e.g., Sum('a') / Count('b'))
    def __add__(self, other: Any) -> AggregateExpression:
        return AggregateExpression(self, operator.add, other)

    def __sub__(self, other: Any) -> AggregateExpression:
        return AggregateExpression(self, operator.sub, other)

    def __mul__(self, other: Any) -> AggregateExpression:
        return AggregateExpression(self, operator.mul, other)

    def __truediv__(self, other: Any) -> AggregateExpression:
        return AggregateExpression(self, operator.truediv, other)


class AggregateExpression:
    """Represents an arithmetic operation between aggregates."""

    def __init__(self, left: Any, op: Callable[..., Any], right: Any) -> None:
        self.left = left
        self.op = op
        self.right = right

    def resolve(self, model: type[Any], columns: Any = None) -> Any:
        left_res = self.left.resolve(model, columns) if hasattr(self.left, "resolve") else self.left
        right_res = self.right.resolve(model, columns) if hasattr(self.right, "resolve") else self.right
        
        return self.op(left_res, right_res)

    def __add__(self, other: Any) -> AggregateExpression:
        return AggregateExpression(self, operator.add, other)

    def __sub__(self, other: Any) -> AggregateExpression:
        return AggregateExpression(self, operator.sub, other)

    def __mul__(self, other: Any) -> AggregateExpression:
        return AggregateExpression(self, operator.mul, other)

    def __truediv__(self, other: Any) -> AggregateExpression:
        return AggregateExpression(self, operator.truediv, other)


class Sum(Aggregate):
    function = "SUM"


class Avg(Aggregate):
    function = "AVG"


class Count(Aggregate):
    function = "COUNT"


class Min(Aggregate):
    function = "MIN"


class Max(Aggregate):
    function = "MAX"
