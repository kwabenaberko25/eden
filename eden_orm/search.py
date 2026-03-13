"""
Eden ORM - Full-Text Search

PostgreSQL-based full-text search integration.
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Represents a search result."""
    id: Any
    relevance: float
    model_instance: Optional[Any] = None


class FullTextSearchEngine:
    """PostgreSQL full-text search integration."""
    
    def __init__(self):
        self.indexed_fields = {}  # {model: [fields]}
    
    def register_index(self, model_class, fields: List[str]):
        """Register full-text search index for model."""
        self.indexed_fields[model_class.__name__] = fields
        logger.info(f"Registered FTS index for {model_class.__name__}: {fields}")
    
    async def create_index(self, session, model_class, fields: List[str]):
        """Create full-text search index in database."""
        table = model_class.__tablename__
        index_name = f"idx_fts_{table}"
        
        # Build tsvector expression
        field_parts = [f"{field}::text" for field in fields]
        tsvector = " || ' ' || ".join(field_parts)
        
        # Create index
        sql = f"""
        CREATE INDEX IF NOT EXISTS {index_name} 
        ON {table} 
        USING GIN(to_tsvector('english', {tsvector}))
        """
        
        try:
            await session.execute(sql)
            logger.info(f"Created FTS index: {index_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to create FTS index: {e}")
            return False
    
    async def search(
        self,
        session,
        model_class,
        query: str,
        fields: Optional[List[str]] = None,
        limit: int = 20,
    ) -> List[SearchResult]:
        """
        Search using PostgreSQL full-text search.
        
        Args:
            session: Database session
            model_class: Model to search
            query: Search query (plain text converted to tsquery)
            fields: Fields to search (uses registered fields if None)
            limit: Max results
        
        Returns:
            List of SearchResult with relevance scores
        """
        if fields is None:
            fields = self.indexed_fields.get(model_class.__name__, [])
        
        if not fields:
            logger.warning(f"No indexed fields for {model_class.__name__}")
            return []
        
        table = model_class.__tablename__
        
        # Build tsvector expression for scoring
        field_parts = [f"{field}::text" for field in fields]
        tsvector = " || ' ' || ".join(field_parts)
        
        # Build WHERE clause with full-text search
        sql = f"""
        SELECT id, ts_rank(
            to_tsvector('english', {tsvector}),
            plainto_tsquery('english', $1)
        ) as relevance
        FROM {table}
        WHERE to_tsvector('english', {tsvector}) @@
              plainto_tsquery('english', $1)
        ORDER BY relevance DESC
        LIMIT $2
        """
        
        try:
            rows = await session.fetch(sql, query, limit)
            
            results = []
            for row in rows:
                result = SearchResult(
                    id=row['id'],
                    relevance=row['relevance'],
                )
                results.append(result)
            
            logger.info(f"FTS search found {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"FTS search failed: {e}")
            return []


class SearchQueryBuilder:
    """Builds advanced full-text search queries."""
    
    def __init__(self, base_query: str = ""):
        self.terms = []
        self.excluded = []
        self.phrases = []
        self.base_query = base_query
    
    def add_term(self, term: str) -> "SearchQueryBuilder":
        """Add a search term."""
        self.terms.append(term)
        return self
    
    def add_phrase(self, phrase: str) -> "SearchQueryBuilder":
        """Add a phrase (words together)."""
        self.phrases.append(f'"{phrase}"')
        return self
    
    def exclude(self, term: str) -> "SearchQueryBuilder":
        """Exclude results containing term."""
        self.excluded.append(f"-{term}")
        return self
    
    def build(self) -> str:
        """Build final search query."""
        parts = list(self.terms) + self.phrases + self.excluded
        return " ".join(parts) if parts else self.base_query


# Global FTS engine
_fts_engine: Optional[FullTextSearchEngine] = None


def get_fts_engine() -> FullTextSearchEngine:
    """Get global FTS engine instance."""
    global _fts_engine
    if _fts_engine is None:
        _fts_engine = FullTextSearchEngine()
    return _fts_engine


def register_fts_index(model_class, fields: List[str]):
    """Register full-text search index for a model."""
    engine = get_fts_engine()
    engine.register_index(model_class, fields)


class FullTextSearchMixin:
    """
    Mixin to add full-text search to models.
    
    Usage:
        class Article(Model, FullTextSearchMixin):
            __search_fields__ = ["title", "content"]
            title: str
            content: str
    """
    
    __search_fields__: List[str] = []
    
    @classmethod
    async def search(cls, query: str, limit: int = 10) -> List[SearchResult]:
        """Search model with full-text query."""
        from .connection import get_session
        
        engine = get_fts_engine()
        session = await get_session()
        
        return await engine.search(
            session,
            cls,
            query,
            fields=cls.__search_fields__ or None,
            limit=limit,
        )
    
    @classmethod
    async def search_ranked(cls, query: str, limit: int = 10) -> List[SearchResult]:
        """Search with relevance ranking."""
        return await cls.search(query, limit)
