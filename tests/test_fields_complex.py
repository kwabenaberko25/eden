from eden.fields import FieldRegistry, array, enum, file, image, json


def test_json_field_metadata():
    field_obj = json()
    assert field_obj.metadata.db_type is dict
    assert field_obj.metadata.widget == "textarea"


def test_array_field_item_type_metadata():
    field_obj = array(item_type=int)
    assert field_obj.metadata.db_type is list
    assert field_obj.metadata.pattern == "int"


def test_enum_field_choices():
    choices = [("admin", "Administrator"), ("user", "User")]
    field_obj = enum(choices)
    assert field_obj.metadata.choices == choices
    assert field_obj.metadata.widget == "select"


def test_file_and_image_widget():
    assert file().metadata.widget == "file"
    assert image().metadata.widget == "image"


def test_registry_has_complex_helpers():
    assert FieldRegistry.get("json") is json
    assert FieldRegistry.get("array") is array
    assert FieldRegistry.get("enum") is enum
    assert FieldRegistry.get("file") is file
    assert FieldRegistry.get("image") is image
