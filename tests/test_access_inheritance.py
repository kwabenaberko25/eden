import pytest
from eden.db.access import AccessControl, AllowPublic, AllowAuthenticated

class ParentAccess(AccessControl):
    __rbac__ = {
        "read": AllowPublic()
    }

class ChildAccess(ParentAccess):
    # No __rbac__ defined here, it SHOULD inherit from parent
    pass

class IsolatedChild(ParentAccess):
    __rbac__ = {
        "update": AllowAuthenticated()
    }

def test_rbac_inheritance():
    """
    Verifies that RBAC rules are inherited if not defined in the child.
    """
    # Parent has "read"
    assert "read" in ParentAccess.__rbac__
    
    # Child should have "read" (Standard Python inheritance works here because it's just an attribute)
    # BUT if we want to add to it without affecting Parent, we need isolation.
    assert "read" in ChildAccess.__rbac__

def test_rbac_isolation_and_merging():
    """
    Verifies that adding a rule to a child does NOT affect the parent,
    and that a child can add its own rules while keeping the parent's (Merging).
    """
    # Currently, ChildAccess.__rbac__ is the IDENTICAL OBJECT as ParentAccess.__rbac__ 
    # if it's not defined in the class body.
    
    # If I do this:
    ChildAccess.__rbac__["create"] = AllowAuthenticated()
    
    # Parent would be affected! (This is the bug)
    assert "create" in ChildAccess.__rbac__
    assert "create" not in ParentAccess.__rbac__, "Parent RBAC should remain isolated from Child changes"

def test_rbac_explicit_override_merging():
    """
    Verifies that if a child defines __rbac__, it still inherits Parent's rules (Merging).
    """
    # IsolatedChild defined __rbac__ = {"update": ...}
    # It SHOULD also have "read" from Parent.
    assert "update" in IsolatedChild.__rbac__
    assert "read" in IsolatedChild.__rbac__, "Child should merge parent RBAC rules"
