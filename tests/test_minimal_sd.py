import pytest
from eden.db import Model, SoftDeleteMixin

class SimpleSDModel(Model, SoftDeleteMixin):
    __tablename__ = "simple_sd_models"

@pytest.mark.asyncio
async def test_minimal():
     print(f"Model MRO: {Model.__mro__}")
     print(f"SoftDeleteModel MRO: {SimpleSDModel.__mro__}")
     assert True
