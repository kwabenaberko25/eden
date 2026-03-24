import pytest
from eden.db import Model, StringField, Database
from eden.db.validation import ValidatorMixin

class ParentModel(Model):
    __tablename__ = "parent_models"
    email: str = StringField(required=True)
    
    @classmethod
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # Manually add a rule to see if it persists
        cls.rule_required("email", message="Parent email required")

class ChildModel(ParentModel):
    __tablename__ = "child_models"
    name: str = StringField()

@pytest.mark.asyncio
async def test_validation_rule_inheritance(db: Database):
    """
    Verifies that validation rules from a parent model are inherited by the child model.
    """
    # Currently, this will likely fail because ChildModel._validation_rules is reset to {}
    
    # Check ParentModel has the rule
    assert "email" in ParentModel._validation_rules
    assert ParentModel._validation_rules["email"][0].message == "Parent email required"
    
    # Check ChildModel has the rule (inherited)
    assert "email" in ChildModel._validation_rules, "ChildModel should inherit 'email' rule from ParentModel"
    assert ChildModel._validation_rules["email"][0].message == "Parent email required"

@pytest.mark.asyncio
async def test_validation_rule_isolation(db: Database):
    """
    Verifies that adding a rule to a child does NOT affect the parent.
    """
    ChildModel.rule_required("name", message="Child name required")
    
    assert "name" in ChildModel._validation_rules
    assert "name" not in ParentModel._validation_rules, "Adding rule to child should not affect parent"
