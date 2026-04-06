from eden.fields import FieldRegistry, foreign_key, many_to_many, one_to_one


class MockModel:
    pass


def test_foreign_key_field_metadata():
    field_obj = foreign_key(MockModel, related_name="owner")
    assert field_obj.metadata.pattern == "foreign_key"
    assert field_obj.metadata.choices[0][1] == "MockModel"
    assert "related_name:owner" in field_obj.metadata.css_classes


def test_one_to_one_field_metadata():
    field_obj = one_to_one(MockModel)
    assert field_obj.metadata.pattern == "one_to_one"
    assert field_obj.metadata.db_type is MockModel


def test_many_to_many_field_metadata():
    field_obj = many_to_many(MockModel, through="membership")
    assert field_obj.metadata.pattern == "many_to_many"
    assert "through:membership" in field_obj.metadata.css_classes


def test_registry_has_relationship_helpers():
    assert FieldRegistry.get("foreign_key") is foreign_key
    assert FieldRegistry.get("one_to_one") is one_to_one
    assert FieldRegistry.get("many_to_many") is many_to_many
