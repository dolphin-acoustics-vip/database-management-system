import copy
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


@pytest.mark.parametrize("attr, value, expected", [
    ("completed_flag", True, True),
    ("completed_flag", False, False),
])
def test_set_attribute(assignment: models.Assignment, attr: str, value, expected):
    common.test_set_attribute(assignment, attr, value, expected)

@pytest.mark.parametrize("attr, value", [
    ("completed_flag", None),
    ("completed_flag", ""),
    ("completed_flag", "   "),
    ("completed_flag", "not-a-boolean"),
    ("user_id", "this-is-not-a-uuid"),
    ("user_id", 1),
    ("recording_id", "this-is-not-a-uuid"),
    ("recording_id", 1)
])
def test_set_attribute_validation_error(assignment: models.Assignment, attr: str, value):
    common.test_set_attribute_validation_error(assignment, attr, value)


@pytest.mark.parametrize("attr, nullable", [
    ("user_id", False),
    ("recording_id", False)
])
def test_uuid(assignment: models.Assignment, attr: str, nullable: bool):
    common.validate_uuid(assignment, attr, str(uuid.uuid4()), nullable)


@pytest.mark.parametrize("form", [
    ({
        'user_id': str(uuid.uuid4()),
        'recording_id': str(uuid.uuid4()),
    }) ])
def test_insert_or_update(assignment: models.Assignment, form):
    assignment._insert_or_update(form = form, new = True)
    assert str(assignment.user_id) == form['user_id']
    assert str(assignment.recording_id) == form['recording_id']


@pytest.mark.parametrize("attr, value", [
    ("user_id", "this-is-not-a-uuid"),
    ("user_id", 1),
    ("user_id", None),
    ("recording_id", None),
    ("recording_id", "this-is-not-a-uuid"),
    ("recording_id", 1)
])
def test_set_attribute_validation_error(assignment: models.Assignment, attr: str, value):
    common.test_set_attribute_validation_error(assignment, attr, value)

@pytest.mark.parametrize("form", [
    ({
        'user_id': str(uuid.uuid4()),
    }),
    ({
        'recording_id': str(uuid.uuid4()),
    }),
    ({
    }), ])
def test_insert_or_update_attribute_error(assignment: models.Assignment, form):
    with pytest.raises(AttributeError):
        assignment._insert_or_update(form = form, new = False)

def test_complete(assignment: models.Assignment):
    assignment.complete_flag = False
    assignment.complete()
    assert assignment.completed_flag == True

def test_incomplete(assignment: models.Assignment):
    assignment.complete_flag = True
    assignment.incomplete()
    assert assignment.completed_flag == False

def test_unique_name(assignment: models.Assignment):
    assert assignment.unique_name == f"{assignment.recording.unique_name}_{assignment.user.unique_name}"