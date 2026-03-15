"""
Eden — Field Helpers with Vendor-Aware Defaults

Provides utilities for handling field defaults that vary by database vendor.

StringField() Default Max Length:
- PostgreSQL: No hard limit (but 1GB per column), recommend 255 for common text
- MySQL: InnoDB row size 65535 bytes limit, use <= 255 for most columns
- SQLite: No limit, but 255 is conventional for indexing
- Oracle: 4000 bytes for VARCHAR2, so max 4000

Recommendation: Use 255 as default for compatibility, explicitly set larger
max_lengths for descriptive fields (bio, content, etc.).

Example:
    # Default: 255 chars (works everywhere)
    name: Mapped[str] = StringField()
    
    # Longer: Bio field with 1000 chars (still safe elsewhere)
    bio: Mapped[str] = StringField(max_length=1000)
    
    # Database-specific: Content field
    # For PostgreSQL: can use 10000
    # For MySQL: limit to 5000 to stay under row size
    content: Mapped[str] = StringField(max_length=5000)
"""

from typing import Optional

# Database vendor constants
VENDOR_STRING_LENGTH_LIMITS = {
    "postgresql": 1_000_000_000,  # 1 GB per column
    "mysql": 65_535,               # InnoDB row size limit
    "sqlite": 1_000_000,           # No real limit
    "oracle": 4_000,               # VARCHAR2 limit
    "mssql": 8_000,                # Standard VARCHAR
}

DEFAULT_STRING_LENGTH = 255  # Safe default for all vendors


def get_max_length_for_vendor(
    vendor: Optional[str] = None,
    logical_max: int = DEFAULT_STRING_LENGTH,
) -> int:
    """
    Get the appropriate max_length for a StringField based on database vendor.
    
    Args:
        vendor: Database vendor name ('postgresql', 'mysql', 'sqlite', 'oracle', 'mssql')
                If None, returns the safe default (255)
        logical_max: The logical max length you want (e.g., 1000 for a long description)
    
    Returns:
        The safe max_length to use for this vendor
    
    Example:
        # Get vendor from your database URL
        db_url = "mysql+asyncmy://user:pass@localhost/dbname"
        vendor = db_url.split("+")[0].split("://")[0]  # "mysql"
        
        # Get safe default for this vendor
        safe_len = get_max_length_for_vendor(vendor, logical_max=1000)
        # For MySQL: returns 1000 (safe within row limit)
        # For Oracle: returns 1000 (safe within VARCHAR2)
        # For Any: returns min(logical_max, vendor_limit)
    """
    if vendor is None or vendor not in VENDOR_STRING_LENGTH_LIMITS:
        return min(logical_max, DEFAULT_STRING_LENGTH)
    
    vendor_limit = VENDOR_STRING_LENGTH_LIMITS[vendor]
    return min(logical_max, vendor_limit)


def get_database_vendor_from_url(database_url: str) -> Optional[str]:
    """
    Extract database vendor from a SQLAlchemy database URL.
    
    Args:
        database_url: URL like 'postgresql://...', 'mysql+asyncmy://...', etc.
    
    Returns:
        Vendor name ('postgresql', 'mysql', 'sqlite', 'oracle', 'mssql') or None
    
    Example:
        url = "postgresql+asyncpg://localhost/mydb"
        get_database_vendor_from_url(url)  # Returns 'postgresql'
        
        url = "sqlite:///./test.db"
        get_database_vendor_from_url(url)  # Returns 'sqlite'
    """
    if not database_url:
        return None
    
    # Extract scheme part before first + or ://
    scheme_part = database_url.split("+")[0].split("://")[0].lower()
    
    # Normalize common variations
    mapping = {
        "postgresql": "postgresql",
        "postgres": "postgresql",
        "pg": "postgresql",
        "mysql": "mysql",
        "mariadb": "mysql",
        "sqlite": "sqlite",
        "oracle": "oracle",
        "mssql": "mssql",
        "pyodbc": "mssql",
    }
    
    return mapping.get(scheme_part)


# Common string field length recommendations per field type
RECOMMENDED_LENGTHS = {
    "email": 254,              # RFC 5321 standard
    "phone": 20,               # E.164 format + formatting
    "username": 50,            # Typically 30-50 chars
    "slug": 100,               # URL-safe slug
    "country_code": 3,         # ISO 3166-1 alpha-3
    "currency_code": 3,        # ISO 4217
    "timezone": 40,            # IANA timezone names
    "url": 2048,               # HTTP URL limit
    "uuid_string": 36,         # UUID as string + hyphens
    "color_hex": 7,            # #RRGGBB
    "language_code": 5,        # ISO 639-1 + region (en-US)
    "short_name": 50,          # Product name, etc.
    "title": 200,              # Article title, etc.
    "description": 500,        # Brief description
    "content": 5000,           # Longer text content (watch row size!)
}


def get_recommended_length(field_type: str) -> Optional[int]:
    """
    Get the recommended max_length for a common field type.
    
    Args:
        field_type: Type of field ('email', 'username', 'title', 'content', etc.)
    
    Returns:
        Recommended max_length, or None if not found
    
    Example:
        email_len = get_recommended_length("email")  # Returns 254
        title_len = get_recommended_length("title")  # Returns 200
    """
    return RECOMMENDED_LENGTHS.get(field_type.lower())


# ID Convention Documentation
ID_CONVENTION_GUIDE = """
Eden Framework ID Convention:

PRIMARY KEYS
============

Option 1: UUID (Recommended)
    Good for: Distributed systems, privacy-focused apps, horizontal sharding
    
    Example:
        import uuid
        from eden.db.fields import UUIDField
        
        class User(Model):
            id: Mapped[uuid.UUID] = UUIDField(primary_key=True)
    
    Pros:
        - Globally unique without server coordination
        - Works well in distributed/multi-database systems
        - No ID enumeration vulnerabilities
        - Sortable (UUID6/v7) if using newer versions
    
    Cons:
        - Larger than int (16 bytes vs 8 bytes)
        - Harder to read in logs
        - Slower index lookups (larger B-tree nodes)

Option 2: Integer (BigInt)
    Good for: Monolithic applications, better performance needs
    
    Example:
        from sqlalchemy import BigInteger
        
        class Order(Model):
            id: Mapped[int] = IntField(primary_key=True)  # Auto-increment
    
    Pros:
        - Smaller, faster index lookups
        - Human-readable IDs
        - Easier to use in URLs without encoding
        - Better performance on large tables
    
    Cons:
        - Requires coordination (auto-increment, sequences)
        - Can run out (though BigInt has 2^63 values)
        - Vulnerable to ID enumeration
        - Doesn't work well across multiple databases

FOREIGN KEYS
============

Always use the same type as the primary key you're referencing:

    class User(Model):
        id: Mapped[uuid.UUID] = UUIDField(primary_key=True)
    
    class Post(Model):
        id: Mapped[uuid.UUID] = UUIDField(primary_key=True)
        user_id: Mapped[uuid.UUID] = UUIDField(foreign_key="users.id")
        author: Mapped[User] = relationship("User")

COMPOSITE KEYS
==============

For composite primary keys, use consistent types:

    class Vote(Model):
        __table_args__ = (
            PrimaryKeyConstraint("user_id", "post_id"),
        )
        user_id: Mapped[uuid.UUID] = UUIDField(foreign_key="users.id")
        post_id: Mapped[uuid.UUID] = UUIDField(foreign_key="posts.id")

BEST PRACTICES
==============

1. Choose ONE convention for your application
2. Use explicit __tablename__ on models
3. Document composite keys clearly
4. Consider performance implications (int faster than UUID)
5. Use UUID for multi-tenant systems (better isolation)
6. Use int for single-tenant APIs (better performance)
7. Always validate foreign key references
"""
