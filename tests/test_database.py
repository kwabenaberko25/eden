import pytest
from typing import Any
from eden.db import Model, f, Database, inspect, Mapped

class Person(Model):
    __tablename__ = "people"
    name: Mapped[str] = f()
    profile: Mapped["Passport"] = None

class Passport(Model):
    __tablename__ = "passports"
    number: Mapped[str] = f()
    # We'll let Eden infer the 'person' backref from Person.profile
    # person: Mapped["Person"] = None

@pytest.mark.asyncio
async def test_one_to_one_inference():
    """
    Test that singular type hints on both sides result in a One-to-One relationship.
    Currently, Eden might fail to set uselist=False or might create dual foreign keys.
    """
    db = Database("sqlite+aiosqlite:///:memory:")
    await db.connect()
    
    try:
        # Check Person -> Passport
        mapper_person = inspect(Person)
        rel_profile = mapper_person.relationships.get("profile")
        
        assert rel_profile is not None, "Profile relationship not found"
        # This is where it currently fails: it defaults to uselist=True (Many-to-One/Many)
        assert rel_profile.uselist is False, "Profile relationship should be uselist=False (O2O)"
        
        # Check if only one side has the foreign key
        has_person_fk = any(c.name == "person_id" for c in mapper_person.columns)
        
        mapper_passport = inspect(Passport)
        has_passport_fk = any(c.name == "person_id" for c in mapper_passport.columns)
        
        # In a 1:1, usually only one side should have the FK (or we decide which one)
        # We'll see how Eden handles this.
    finally:
        await db.disconnect()

class Company(Model):
    name: Mapped[str] = f()
    # Many-to-One
    employees: Mapped[list["Employee"]] = None

class Employee(Model):
    name: Mapped[str] = f()
    company: Mapped["Company"] = None

@pytest.mark.asyncio
async def test_many_to_one_inference():
    """Verify existing M2O/O2M inference still works."""
    db = Database("sqlite+aiosqlite:///:memory:")
    await db.connect()
    
    try:
        mapper_company = inspect(Company)
        rel_employees = mapper_company.relationships.get("employees")
        assert rel_employees.uselist is True
        
        mapper_employee = inspect(Employee)
        rel_company = mapper_employee.relationships.get("company")
        assert rel_company.uselist is False
    finally:
        await db.disconnect()
