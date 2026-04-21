import asyncio
from sqlalchemy import select, Column, Integer, String, Boolean
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class MockModel(Base):
    __tablename__ = 'test'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    deleted_at = Column(Integer, nullable=True)
    tenant_id = Column(Integer)

def get_base_select(tenantless=False):
    stmt = select(MockModel)
    if not tenantless:
        stmt = stmt.where(MockModel.tenant_id == 1)
    return stmt

# Simulate QuerySet creation
stmt = get_base_select()

# Simulate user adding filters
stmt = stmt.where(MockModel.name == 'test')

# Now user calls .include_tenantless()
old_base_stmt = get_base_select(tenantless=False)

def str_expr(e):
    return str(e.compile(compile_kwargs={"literal_binds": True}))

old_base_criteria_strs = {str_expr(e) for e in old_base_stmt._where_criteria}

new_stmt = select(MockModel)  # Simulating get_base_select(tenantless=True)
user_criteria = [expr for expr in stmt._where_criteria if str_expr(expr) not in old_base_criteria_strs]

if user_criteria:
    new_stmt = new_stmt.where(*user_criteria)

print("Stmt where:", stmt._where_criteria)
print("New stmt where:", new_stmt._where_criteria)
print("New query:", new_stmt.compile(compile_kwargs={"literal_binds": True}))
