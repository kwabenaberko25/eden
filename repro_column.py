
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import DeclarativeBase
from eden.db.lookups import EdenComparator

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "user"
    id = Column(Integer, primary_key=True)
    name = Column(String(50), comparator_factory=EdenComparator)

print("Model with Column defined successfully.")
