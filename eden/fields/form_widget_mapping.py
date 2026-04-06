from __future__ import annotations

from eden.fields.base import FieldMetadata


WIDGET_MAP: dict[str, str] = {
    "input": "text",
    "textarea": "textarea",
    "email": "email",
    "password": "password",
    "checkbox": "checkbox",
    "tel": "tel",
    "url": "url",
    "datetime-local": "datetime-local",
    "date": "date",
    "time": "time",
    "file": "file",
    "select": "select",
    "relationship": "select",
    "image": "file",
}


def widget_for_field(metadata: FieldMetadata) -> str:
    return WIDGET_MAP.get(metadata.widget, "text")


def input_type_for_field(metadata: FieldMetadata) -> str:
    if metadata.widget in {"textarea", "select"}:
        return metadata.widget
    return WIDGET_MAP.get(metadata.widget, "text")
