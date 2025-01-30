from unittest import mock
import pytest
import uuid
from . import factories
from . import common
from ..app import exception_handler
from ..app import models


UUID_TEST = uuid.uuid4()
EMPTY_CHARACTERS = common.EMPTY_CHARACTERS

@pytest.fixture
def recording_platform():
    return factories.RecordingPlatformFactory.create()

@pytest.mark.parametrize("attr, value, expected", [
    ("name", "TestName", "TestName"),
    ("name", " TestName", "TestName"),
    ("name", "TestName ", "TestName"),
    ("name", " Test Name ", "Test Name")
])
def test_set_attribute(recording_platform: models.RecordingPlatform, attr: str, value, expected):
    setattr(recording_platform, attr, value)
    assert getattr(recording_platform, attr) == expected

@pytest.mark.parametrize("attr, value", [
    ("name", 1),
    ("name", None),
    ("name", ""),
    ("name", "   ")
])
def test_validation_error(recording_platform: models.RecordingPlatform, attr: str, value):
    with pytest.raises(exception_handler.ValidationError):
        setattr(recording_platform, attr, value)

@pytest.mark.parametrize("form, new", [
    ({
        "name": "Test Name"
    }, True),
    ({
        "name": "Test Name"
    }, False)
])
def test_insert_or_update(recording_platform: models.RecordingPlatform, form, new):
    recording_platform._insert_or_update(form = form, new = new)
    assert recording_platform.name == form["name"]

def test_updated_by_id(recording_platform: models.RecordingPlatform):
    user_id = uuid.uuid4()
    recording_platform.updated_by_id = user_id
    assert recording_platform.updated_by_id == user_id

@pytest.mark.parametrize("c", EMPTY_CHARACTERS)
def test_set_updated_by_id_empty(recording_platform: models.RecordingPlatform, c: str):
    recording_platform.updated_by_id = c
    assert recording_platform.updated_by_id == None

def test_set_updated_by_id_wrong_type(recording_platform: models.RecordingPlatform):
    with pytest.raises(exception_handler.ValidationError):
        recording_platform.updated_by_id = "this-is-not-a-uuid"

def test_to_dict(recording_platform: models.RecordingPlatform):
    expected = {
        "id": recording_platform.id,
        "name": recording_platform.name,
        "updated_by_id": recording_platform.updated_by_id,
        "updated_by": recording_platform.updated_by
    }
    assert expected == recording_platform._to_dict()