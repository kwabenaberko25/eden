from datetime import datetime

from eden.fields import FieldRegistry, auto_now, auto_now_update, date, datetime as dt, time


def test_datetime_field_widget():
    field_obj = dt()
    assert field_obj.metadata.db_type.__name__ == "datetime"
    assert field_obj.metadata.widget == "datetime-local"


def test_date_and_time_fields():
    assert date().metadata.widget == "date"
    assert time().metadata.widget == "time"


def test_auto_now_default_factory():
    field_obj = auto_now()
    assert callable(field_obj.metadata.default_factory)


def test_registry_has_temporal_helpers():
    assert FieldRegistry.get("datetime") is dt
    assert FieldRegistry.get("date") is date
    assert FieldRegistry.get("time") is time
    assert FieldRegistry.get("auto_now") is auto_now
    assert FieldRegistry.get("auto_now_update") is auto_now_update
