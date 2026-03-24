import pytest
from eden.db import Model, StringField, Database, Mapped
from eden.db.validation import ValidatorMixin

class InhParent(Model):
    __abstract__ = True
    email: Mapped[str] = StringField(required=True)

class InhChild(InhParent):
    __tablename__ = "inh_children"
    name: Mapped[str] = StringField(min_length=3)

@pytest.mark.asyncio
async def test_validation_rule_inheritance(db: Database):
    """
    Verifies that validation rules from a parent model are inherited by the child model.
    """
    # Check InhParent has the rule (discovered from StringField)
    assert "email" in InhParent._validation_rules
    assert any(r.rule_type == "required" for r in InhParent._validation_rules["email"])
    
    # Check InhChild has the rule (inherited)
    assert "email" in InhChild._validation_rules, "InhChild should inherit 'email' rule from InhParent"
    assert any(r.rule_type == "required" for r in InhChild._validation_rules["email"])
    
    # Check InhChild also has its own rule
    assert "name" in InhChild._validation_rules
    assert any(r.rule_type == "min_length" for r in InhChild._validation_rules["name"])

@pytest.mark.asyncio
async def test_validation_rule_isolation(db: Database):
    """
    Verifies that adding a rule to a child does NOT affect the parent.
    """
    InhChild.rule_email("name", message="Invalid email for name")
    
    # Name should have min_length (discovered) and email (manually added)
    assert any(r.rule_type == "email" for r in InhChild._validation_rules["name"])
    
    # Parent should NOT have the email rule for name
    if "name" in InhParent._validation_rules:
        assert not any(r.rule_type == "email" for r in InhParent._validation_rules["name"])
    else:
        assert "name" not in InhParent._validation_rules
