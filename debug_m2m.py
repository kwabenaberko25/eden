import asyncio
from eden.db import Model, f, ManyToManyField, Mapped
from typing import List

try:
    print("Defining M2MDummy...")
    class M2MDummy(Model):
        name: str = f(max_length=50)
        others: Mapped[List["M2MOther"]] = ManyToManyField("M2MOther", back_populates="dummies")

    print("Defining M2MOther...")
    class M2MOther(Model):
        title: str = f(max_length=100)
        dummies: Mapped[List["M2MDummy"]] = ManyToManyField("M2MDummy", back_populates="others")

    print("Tables in metadata:")
    for t in Model.registry.metadata.tables.keys():
        print(" -", t)

    print("Configuring mappers...")
    from sqlalchemy.orm import configure_mappers
    configure_mappers()
    print("Success!")
except Exception as e:
    print("Execution failed. Saving traceback to full_trace.txt")
    import traceback
    with open("full_trace.txt", "w") as f:
        traceback.print_exc(file=f)
