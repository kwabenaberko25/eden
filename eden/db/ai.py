"""
Eden — AI & Vector Extensions
Native support for embeddings and semantic search.
"""

from typing import Any, List, Optional, Union
from sqlalchemy import Column
from sqlalchemy.orm import Mapped, mapped_column
try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    Vector = None

from eden.db.base import Model
from eden.db.fields import f

class VectorModel(Model):
    """
    Base model for AI-powered models requiring vector embeddings.
    """
    __abstract__ = True

    @classmethod
    def vector_field(
        cls, 
        dimensions: int, 
        widget: str = "vector",
        **kwargs
    ) -> Any:
        """
        Helper to define a vector column.
        """
        if Vector is None:
            raise ImportError(
                "pgvector is required for VectorModel. "
                "Install it with: uv add pgvector"
            )
        return f(Vector(dimensions), widget=widget, **kwargs)

    @classmethod
    async def semantic_search(
        cls,
        embedding: List[float],
        field: str = "embedding",
        limit: int = 10,
        session: Optional[Any] = None
    ) -> List[Any]:
        """
        Perform a semantic search using cosine distance.
        """
        from sqlalchemy import select
        
        async with cls._provide_session() as sess:
            current_session = session or sess
            column = getattr(cls, field)
            # pgvector uses <=> for cosine distance (smaller is better/more similar)
            stmt = select(cls).order_by(column.cosine_distance(embedding)).limit(limit)
            
            result = await current_session.execute(stmt)
            return list(result.scalars().all())



def VectorField(dimensions: int, **kwargs) -> Any:
    """Shortcut for f(Vector(dimensions), ...)"""
    if Vector is None:
        raise ImportError(
            "pgvector is required for VectorField. "
            "Install it with: uv add pgvector"
        )
    return f(Vector(dimensions), **kwargs)
