import sys
from eden.db import Model, StringField, Mapped
from eden.db.schema import ValidationScanner
from sqlalchemy import event, DDL

class InhParent(Model):
    __abstract__ = True
    email: Mapped[str] = StringField(required=True)

class InhChild(InhParent):
    __tablename__ = "inh_children"
    name: Mapped[str] = StringField(min_length=3)

with open("scanner_out.txt", "w") as f:
    f.write(f"InhParent rules: {InhParent._validation_rules}\n")
    f.write(f"InhChild rules: {InhChild._validation_rules}\n")
    
    # Check if 'email' is in both
    f.write(f"email in Parent: {'email' in InhParent._validation_rules}\n")
    f.write(f"email in Child: {'email' in InhChild._validation_rules}\n")
    
    # Check uniqueness
    if 'email' in InhChild._validation_rules:
        f.write(f"InhChild 'email' rule count: {len(InhChild._validation_rules['email'])}\n")
