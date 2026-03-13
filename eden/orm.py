"""
Eden — ORM Package
A unified, clean interface over SQLAlchemy.

⚠️  DEPRECATION NOTICE:
    This module is deprecated in favor of the explicit import paths:
    
    from eden.db import Model, QuerySet, Database, etc.
    from eden.db import F, Q  # Query utilities
    from eden.db import StringField, IntField, etc.  # Field types
    from eden.db import Page, SoftDeleteMixin, MigrationManager
    
    from eden.orm import ...  # Still works for backward compatibility,
                             # but will be removed in v1.0.0

Why? Explicit imports reduce the number of dependencies loaded at startup
and make it clear which features are core vs optional.

Migration path:
    OLD: from eden.orm import Model
    NEW: from eden.db import Model
    
    OLD: from eden import Model
    NEW: from eden.db import Model  (or from eden import Model for backward compat)

The eden.orm module will continue to re-export from eden.db for 1-2 releases.
After that, users must import from eden.db directly.
"""

from eden.db import *
from eden.db.ai import VectorModel, VectorField
from eden.db.access import AccessControl, PermissionRule, AllowAll, AllowOwner, AllowRoles

from eden.db.migrations import MigrationManager
