"""
Eden — Full-Text Search Utilities
"""

from typing import List, Optional, Any


class SearchQueryBuilder:
    """
    Builds advanced full-text search queries for PostgreSQL.
    
    Usage:
        query = SearchQueryBuilder() \
            .add_term("eden") \
            .add_phrase("web framework") \
            .exclude("legacy") \
            .build()
        # -> 'eden "web framework" -legacy'
        
        await Product.query().search_ranked(query).all()
    """

    def __init__(self, base_query: str = ""):
        self.terms: List[str] = []
        self.excluded: List[str] = []
        self.phrases: List[str] = []
        self.base_query = base_query

    def add_term(self, term: str) -> "SearchQueryBuilder":
        """Add a simple search term."""
        if term:
            # We remove punctuation that breaks websearch/tsquery
            # and keep it clean for websearch_to_tsquery
            clean_term = term.replace('"', '').replace("'", "")
            self.terms.append(clean_term)
        return self

    def add_phrase(self, phrase: str) -> "SearchQueryBuilder":
        """Add a multi-word phrase that must appear together."""
        if phrase:
            self.phrases.append(f'"{phrase}"')
        return self

    def exclude(self, term: str) -> "SearchQueryBuilder":
        """Exclude results containing this term."""
        if term:
            self.excluded.append(f"-{term}")
        return self

    def build(self) -> str:
        """Combine all terms into a PostgreSQL-compatible search string."""
        parts = list(self.terms) + self.phrases + self.excluded
        return " ".join(parts) if parts else self.base_query

    def to_tsquery(self, language: str = "english") -> Any:
        """
        Convert the builder state into a SQLAlchemy websearch_to_tsquery expression.
        """
        from sqlalchemy import func
        return func.websearch_to_tsquery(language, self.build())

    def apply(self, model_cls: Any, fields: Optional[List[str]] = None, language: str = "english") -> Any:
        """
        Generate a SQLAlchemy boolean expression (Vector @@ Query) for the given model and fields.
        """
        from sqlalchemy import func, inspect as sa_inspect
        from sqlalchemy.types import String, Text

        # Determine fields to search
        if not fields:
            fields = getattr(model_cls, "__search_fields__", None)

        if not fields:
            mapper = sa_inspect(model_cls)
            fields = [
                col.name
                for col in mapper.columns
                if isinstance(col.type, (String, Text))
            ]

        if not fields:
            raise ValueError(f"No searchable text fields found for {model_cls.__name__}")

        # Build search vector expression
        cols = [getattr(model_cls, f) for f in fields]
        concatenated = func.concat_ws(" ", *cols)
        search_vector = func.to_tsvector(language, concatenated)
        
        return search_vector.op("@@")(self.to_tsquery(language))
