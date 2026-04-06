from eden.fields import FieldMetadata, input_type_for_field, widget_for_field


def test_widget_for_field_default():
    metadata = FieldMetadata(widget="unknown")
    assert widget_for_field(metadata) == "text"


def test_widget_for_field_known():
    metadata = FieldMetadata(widget="email")
    assert widget_for_field(metadata) == "email"


def test_input_type_for_field_textarea():
    metadata = FieldMetadata(widget="textarea")
    assert input_type_for_field(metadata) == "textarea"


def test_input_type_for_field_checkbox():
    metadata = FieldMetadata(widget="checkbox")
    assert input_type_for_field(metadata) == "checkbox"
