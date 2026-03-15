from eden.db import Model, f
from sqlalchemy.orm import Mapped

try:
    class Parent(Model):
        name: str = f()
        children: Mapped[list["Child"]] = f(back_populates="parent")

    class Child(Model):
        name: str = f()
        parent: Mapped["Parent"] = f(back_populates="children")
    
    print("Success")
except Exception as e:
    import traceback
    traceback.print_exc()
