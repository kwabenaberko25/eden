import asyncio
from eden.db.query import QuerySet
from sqlalchemy.orm import DeclarativeBase
from eden.db import Model, AllowPublic
from sqlalchemy import Column, String

class TestModel(Model):
    __tablename__ = "test_rbac_print"
    __rbac__ = {"read": AllowPublic()}
    name = Column(String)

async def main():
    print("STARTING TEST")
    qs = TestModel.query()
    try:
        await qs.all()
    except Exception as e:
        print(f"Caught expected error or not: {e}")
    print("ENDING TEST")

if __name__ == "__main__":
    asyncio.run(main())
