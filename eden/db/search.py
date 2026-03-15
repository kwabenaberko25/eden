"""
Eden — Full-Text Search Utilities
"""

from typing import List, Optional


class SearchQueryBuilder:
    """
    Builds advanced full-text search queries for PostgreSQL.
    
    Usage:
        query = SearchQueryBuilder() \\
            .add_term("eden") \\
            .add_phrase("web framework") \\
            .exclude("legacy") \\
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
            self.terms.append(term)
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
