import pytest
from eden.db.validation import ValidatorMixin, ValidationRule

class SimpleParent(ValidatorMixin):
    _validation_rules = {}

SimpleParent.rule_required("email", message="Parent email required")

class SimpleChild(SimpleParent):
    pass

def test_validation_rule_inheritance_simple():
    """
    Verifies that validation rules from a parent model are inherited by the child model.
    """
    # Check parent
    assert "email" in SimpleParent._validation_rules
    assert SimpleParent._validation_rules["email"][0].message == "Parent email required"
    
    # Check child (Should fail currently)
    assert "email" in SimpleChild._validation_rules
    assert SimpleChild._validation_rules["email"][0].message == "Parent email required"

def test_validation_rule_isolation_simple():
    """
    Verifies adding a rule to a child does NOT affect its parent.
    """
    SimpleChild.rule_required("name", message="Child name required")
    
    assert "name" in SimpleChild._validation_rules
    assert "name" not in SimpleParent._validation_rules
