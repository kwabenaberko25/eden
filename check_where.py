import asyncio
from sqlalchemy import select, Column, Integer, String, Boolean
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class MockModel(Base):
    __tablename__ = 'test'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    deleted_at = Column(Integer, nullable=True)

stmt = select(MockModel).where(MockModel.deleted_at == None)
stmt = stmt.where(MockModel.name == 'test')

# Now pretend we want to rebuild it WITHOUT deleted_at
new_stmt = select(MockModel)
new_stmt = new_stmt.where(*stmt._where_criteria)

print("Stmt where:", stmt._where_criteria)
print("New stmt where:", new_stmt._where_criteria)
print("New query:", new_stmt.compile(compile_kwargs={"literal_binds": True}))
