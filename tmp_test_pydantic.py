from pydantic import BaseModel, create_model, Field
from typing import Optional

def test():
    fields = {
        "username": (str, Field(default=...)),
        "age": (Optional[int], Field(default=None))
    }
    User = create_model("User", **fields)
    user = User(username="test")
    print(user.model_dump())

if __name__ == "__main__":
    test()
