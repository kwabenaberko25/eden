"""
Eden — Database Aggregates

Django-style aggregation functions that wrap SQLAlchemy's func calls.
These allow for expressive data analysis in QuerySet.aggregate() and QuerySet.annotate().
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import func


class Aggregate:
    """Base class for aggregation functions."""

    function: str = ""

    def __init__(self, field: str, alias: str | None = None) -> None:
        self.field = field
        self.alias = alias

    def resolve(self, model: type[Any]) -> Any:
        column = getattr(model, self.field, None)
        if column is None:
            raise ValueError(f"'{model.__name__}' has no field '{self.field}'")

        agg_func = getattr(func, self.function.lower())
        expr = agg_func(column)

        if self.alias:
            return expr.label(self.alias)
        return expr.label(f"{self.field}__{self.function.lower()}")


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
