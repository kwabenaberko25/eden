import re
from typing import Dict, Any
from datetime import datetime, timezone

# Internal sentinel for missing values
_MISSING = object()


def get_utc_now() -> datetime:
    """
    Get current time in UTC as a naive datetime (no tzinfo).
    
    This ensures consistency across all timestamp operations:
    - Database stores naive UTC times
    - Comparisons don't have timezone confusion  
    - Tests get predictable results
    
    Returns:
        datetime: Current UTC time without tzinfo
    """
    return datetime.now(timezone.utc).replace(tzinfo=None).replace(tzinfo=None)


def renumber_sql_params(sql: str, offset: int = 0) -> str:
    """
    Renumbers $N placeholders in a PostgreSQL SQL string.
    Useful for merging SQL fragments with parameters.
    
    Example:
        renumber_sql_params("WHERE id = $1 AND name = $2", 2)
        # Returns: "WHERE id = $3 AND name = $4"
    """
    def replace(match):
        num = int(match.group(1))
        return f"${num + offset}"
    
    return re.sub(r"\$(\d+)", replace, sql)

def merge_raw_sql(base_sql: str, extra_sql: str, base_params: list, extra_params: list) -> tuple[str, list]:
    """
    Merges two raw SQL fragments with their parameters, renumbering placeholders.
    """
    offset = len(base_params)
    new_extra_sql = renumber_sql_params(extra_sql, offset)
    return f"{base_sql} {new_extra_sql}", base_params + extra_params
