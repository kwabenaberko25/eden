import builtins
from decimal import Decimal

from eden.fields import FieldRegistry, bool, decimal, float, int


def test_int_field_metadata():
    field_obj = int(min_value=1, max_value=10, unique=True)
    assert field_obj.metadata.db_type is builtins.int
    assert field_obj.metadata.min_value == 1
    assert field_obj.metadata.max_value == 10
    assert field_obj.metadata.unique is True
    assert field_obj.metadata.widget == "number"


def test_float_field_metadata():
    field_obj = float(nullable=True, default=1.5)
    assert field_obj.metadata.db_type is builtins.float
    assert field_obj.metadata.nullable is True
    assert field_obj.metadata.default == 1.5


def test_decimal_field_metadata():
    field_obj = decimal(default=Decimal("9.99"))
    assert field_obj.metadata.db_type is Decimal
    assert field_obj.metadata.default == Decimal("9.99")


def test_bool_field_widget():
    field_obj = bool(default=False)
    assert field_obj.metadata.db_type is builtins.bool
    assert field_obj.metadata.widget == "checkbox"


def test_registry_has_numeric_helpers():
    assert FieldRegistry.get("int") is int
    assert FieldRegistry.get("float") is float
    assert FieldRegistry.get("decimal") is decimal
    assert FieldRegistry.get("bool") is bool
