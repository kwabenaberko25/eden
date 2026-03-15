from typing import Mapped
from eden.db import Model as EdenModel, StringField

class Product(EdenModel):
    """
    Product model.
    """
    # Use Mapped[type] for standard fields (auto-mapped via type_annotation_map)
    name: Mapped[str]

    # Use Field helpers for specific constraints
    # email: Mapped[str] = StringField(max_length=255, unique=True)
