
import asyncio
from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, ColumnProperty
from eden.db.lookups import EdenComparator

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "user"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), comparator_factory=EdenComparator)

print("Model defined successfully.")
