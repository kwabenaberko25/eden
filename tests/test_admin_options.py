import pytest
from eden.admin.options import ModelAdmin
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class DummyModel(Base):
    __tablename__ = "dummy"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    email = Column(String)
    created_at = Column(Integer)

class Box(Base):
    __tablename__ = "boxes"
    id = Column(Integer, primary_key=True)

class Church(Base):
    __tablename__ = "churches"
    id = Column(Integer, primary_key=True)

class Buzz(Base):
    __tablename__ = "buzzes"
    id = Column(Integer, primary_key=True)
    
class City(Base):
    __tablename__ = "cities"
    id = Column(Integer, primary_key=True)
    
class Boy(Base):
    __tablename__ = "boys"
    id = Column(Integer, primary_key=True)

class VehicleModel(Base):
    __tablename__ = "vehicle_models"
    id = Column(Integer, primary_key=True)
    
class UserAccount(Base):
    __tablename__ = "user_accounts"
    id = Column(Integer, primary_key=True)

def test_get_list_display():
    admin = ModelAdmin()
    admin.list_display = ["name", "email"]
    # Should return explicit list_display
    assert admin.get_list_display(DummyModel) == ["name", "email"]
    
    admin2 = ModelAdmin()
    # Should auto-detect from model columns, excluding 'id' and limit to 6
    columns = admin2.get_list_display(DummyModel)
    assert columns == ["name", "email", "created_at"]
    
    # invalid model, returns ["id"]
    class InvalidModel:
        pass
    assert admin2.get_list_display(InvalidModel) == ["id"]

def test_get_form_fields():
    admin = ModelAdmin()
    fields = admin.get_form_fields(DummyModel)
    # excludes 'id', 'created_at', 'updated_at' by default
    assert "name" in fields
    assert "email" in fields
    assert "id" not in fields
    assert "created_at" not in fields
    
    # invalid model, returns []
    class InvalidModel:
        pass
    assert admin.get_form_fields(InvalidModel) == []

def test_get_verbose_name():
    admin = ModelAdmin()
    admin.verbose_name = "Super Dummy"
    assert admin.get_verbose_name(DummyModel) == "Super Dummy"
    
    admin2 = ModelAdmin()
    assert admin2.get_verbose_name(DummyModel) == "Dummy"
    
    # Test CamelCase parsing
    assert admin2.get_verbose_name(UserAccount) == "User Account"
    
    # Test "Model" suffix removal
    assert admin2.get_verbose_name(VehicleModel) == "Vehicle"

def test_get_verbose_name_plural():
    admin = ModelAdmin()
    admin.verbose_name_plural = "Super Dummies"
    assert admin.get_verbose_name_plural(DummyModel) == "Super Dummies"
    
    admin2 = ModelAdmin()
    
    # standard 's' ending
    assert admin2.get_verbose_name_plural(UserAccount) == "User Accounts"
    
    # ends with 'x'
    assert admin2.get_verbose_name_plural(Box) == "Boxes"
    
    # ends with 'ch'
    assert admin2.get_verbose_name_plural(Church) == "Churches"
    
    # ends with 'z'
    assert admin2.get_verbose_name_plural(Buzz) == "Buzzes"
    
    # ends with 'y' -> 'ies'
    assert admin2.get_verbose_name_plural(City) == "Cities"
    
    # ends with 'ay', 'oy', etc -> 'ys'
    assert admin2.get_verbose_name_plural(Boy) == "Boys"

def test_get_list_header_stats():
    admin = ModelAdmin()
    assert admin.get_list_header_stats(DummyModel) == []
