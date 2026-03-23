"""
Eden — Tenancy Exceptions
"""

from eden.db.session import DatabaseError

class TenancyIsolationError(DatabaseError):
    """
    Raised when a tenant-isolated model is accessed without a valid 
    tenant context in strict mode.
    """
    pass
