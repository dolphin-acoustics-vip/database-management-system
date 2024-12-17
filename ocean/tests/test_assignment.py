import datetime
import uuid
import pytest
from . import factories
from ..app import models
from ..app import exception_handler
from . import common

EMPTY_CHARACTERS = common.EMPTY_CHARACTERS

@pytest.fixture
def assignment():
    return factories.AssignmentFactory.create()

def test_hasattr_row_start(assignment: models.Assignment):
    assert hasattr(assignment, "row_start")
    assert hasattr(assignment, "get_row_start")
    assert hasattr(assignment, "get_row_start_pretty")

def test_hasattr_created_datetime(assignment: models.Assignment):
    assert hasattr(assignment, "created_datetime")
    assert hasattr(assignment, "get_created_datetime")
    assert hasattr(assignment, "get_created_datetime_pretty")

def test_hasattr_getters(assignment: models.Assignment):
    assert hasattr(assignment, "get_user_id")
    assert hasattr(assignment, "get_user")
    assert hasattr(assignment, "get_recording_id")
    assert hasattr(assignment, "get_recording")
    assert hasattr(assignment, "get_completed_flag")

def test_hasattr_setters(assignment: models.Assignment):
    assert hasattr(assignment, "set_user_id")
    assert hasattr(assignment, "set_user")
    assert hasattr(assignment, "set_recording_id")
    assert hasattr(assignment, "set_recording")
    
@pytest.mark.parametrize("value", [True, False])
def test_get_completed_flag(assignment: models.Assignment, value: bool):
    assignment.completed_flag = value
    assert assignment.get_completed_flag() == value
    
def set_complete(assignment: models.Assignment):
    assert hasattr(assignment, "set_completed")
    assignment.completed_flag = None
    assignment.set_complete()
    assert assignment.completed_flag == True

def set_not_completed(assignment: models.Assignment):
    assert hasattr(assignment, "set_incomplete")
    assignment.completed_flag = None
    assignment.set_incomplete()
    assert assignment.completed_flag == False

def test_set_user_id(assignment: models.Assignment):
    user_id = uuid.uuid4()
    assignment.set_user_id(user_id)
    assert assignment.user_id == user_id
    
@pytest.mark.parametrize("c", EMPTY_CHARACTERS)
def test_set_user_id_none(assignment: models.Assignment, c: str):
    with pytest.raises(exception_handler.WarningException):
        assignment.set_user_id(c)

def test_set_user_id_wrong_type(assignment: models.Assignment):
    with pytest.raises(exception_handler.WarningException):
        assignment.set_user_id("this-is-not-a-uuid")

def test_set_user(assignment: models.Assignment):
    user = factories.UserFactory.create()
    assignment.set_user(user)
    assert assignment.user == user

def test_set_user_none(assignment: models.Assignment):
    with pytest.raises(exception_handler.WarningException):
        assignment.set_user(None)

def test_set_user_wrong_type(assignment: models.Assignment):
    with pytest.raises(ValueError):
        assignment.set_user(factories.SpeciesFactory.create())

def test_set_recording_id(assignment: models.Assignment):
    recording_id = uuid.uuid4()
    assignment.set_recording_id(recording_id)
    assert assignment.recording_id == recording_id
    
@pytest.mark.parametrize("c", EMPTY_CHARACTERS)
def test_set_recording_id_none(assignment: models.Assignment, c: str):
    with pytest.raises(exception_handler.WarningException):
        assignment.set_recording_id(c)

def test_set_recording_id_wrong_type(assignment: models.Assignment):
    with pytest.raises(exception_handler.WarningException):
        assignment.set_recording_id("this-is-not-a-uuid")

def test_set_user(assignment: models.Assignment):
    recording = factories.RecordingFactory.create()
    assignment.set_recording(recording)
    assert assignment.recording == recording

def test_set_recording_none(assignment: models.Assignment):
    with pytest.raises(exception_handler.WarningException):
        assignment.set_recording(None)

def test_set_recording_wrong_type(assignment: models.Assignment):
    with pytest.raises(ValueError):
        assignment.set_recording(factories.SpeciesFactory.create())
