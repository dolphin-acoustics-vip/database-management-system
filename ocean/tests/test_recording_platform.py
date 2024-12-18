import pytest
import uuid
from . import factories
from . import common
from ..app import exception_handler
from ..app import models

EMPTY_CHARACTERS = common.EMPTY_CHARACTERS

@pytest.fixture
def recording_platform():
    return factories.RecordingPlatformFactory.create()

def test_hasattr_updated_by(recording_platform):
    assert hasattr(recording_platform, "updated_by_id")
    assert hasattr(recording_platform, "updated_by")
    assert hasattr(recording_platform, "set_updated_by_id")
        
def test_set_updated_by_id(recording_platform: models.RecordingPlatform):
    user_id = uuid.uuid4()
    recording_platform.set_updated_by_id(user_id)
    assert recording_platform.updated_by_id == user_id

@pytest.mark.parametrize("c", EMPTY_CHARACTERS)
def test_set_updated_by_id_empty(recording_platform: models.RecordingPlatform, c: str):
    with pytest.raises(exception_handler.WarningException):
        recording_platform.set_updated_by_id(c)

def test_set_updated_by_id_wrong_type(recording_platform: models.RecordingPlatform):
    with pytest.raises(exception_handler.WarningException):
        recording_platform.set_updated_by_id("this-is-not-a-uuid")
        
def test_set_name(recording_platform: models.RecordingPlatform):
    recording_platform.set_name("TestName")
    assert recording_platform.name == "TestName"

@pytest.mark.parametrize("c", EMPTY_CHARACTERS)
def test_set_name_empty(recording_platform: models.RecordingPlatform, c: str):
    with pytest.raises(exception_handler.WarningException):
        recording_platform.set_name(c)

def test_set_name_wrong_type(recording_platform: models.RecordingPlatform):
    with pytest.raises(ValueError):
        recording_platform.set_name(1)
        
def test_get_name(recording_platform: models.RecordingPlatform):
    recording_platform.name = "TestName"
    assert recording_platform.get_name() == "TestName"

def test_get_name_none(recording_platform: models.RecordingPlatform):
    recording_platform.name = None
    assert recording_platform.get_name() == ""