# Standard library imports
import copy
import uuid
import datetime
import os

# Third-party libraries
import pandas as pd
import pytest

# Local application imports
from . import factories
from . import common
from ..app import exception_handler
from ..app import models
from ..app import utils
from ..app import filespace_handler

EMPTY_CHARACTERS = common.EMPTY_CHARACTERS
DATE_FORMAT = common.DATE_FORMAT

@pytest.fixture
def recording():
    return factories.RecordingFactory.create()

@pytest.mark.parametrize("attr, value, expected", [
    ("status", "Unassigned", "Unassigned"),
    ("status", "In Progress", "In Progress"),
    ("status", "Awaiting Review", "Awaiting Review"),
    ("status", "Reviewed", "Reviewed"),
    ("status", "On Hold", "On Hold"),
    ("notes", "TestName", "TestName"),
    ("notes", " TestName\nHello\n\tThis is a new line.", "TestName\nHello\n\tThis is a new line."),
    ("notes", "TestName\nHello\n\tThis is a new line. ", "TestName\nHello\n\tThis is a new line."),
    ("notes", "TestName\nHello\n\tThis is a new line.", "TestName\nHello\n\tThis is a new line.")
])
def test_set_attribute(recording: models.Recording, attr: str, value, expected):
    setattr(recording, attr, value)
    assert getattr(recording, attr) == expected

@pytest.mark.parametrize("attr, value", [
    ("status", 1),
    ("status", None),
    ("status", ""),
    ("status", "   "),
    ("encounter_id", "this-is-not-a-uuid"),
    ("encounter_id", 1),
    ("encounter_id", None),
    ("encounter_id", ""),
    ("encounter_id", "   "),
    ("recording_file_id", "this-is-not-a-uuid"),
    ("recording_file_id", 1),
    ("selection_table_file_id", "this-is-not-a-uuid"),
    ("selection_table_file_id", 1),
    ("updated_by_id", "this-is-not-a-uuid"),
    ("updated_by_id", 1)
])
def test_set_attribute_validation_error(recording: models.Recording, attr: str, value):
    common.test_set_attribute_validation_error(recording, attr, value)

@pytest.mark.parametrize("attr, nullable", [
    ("encounter_id", False),
    ("recording_file_id", True),
    ("selection_table_file_id", True),
    ("updated_by_id", True)
])
def test_uuid(recording: models.Recording, attr: str, nullable: bool):
    common.validate_uuid(recording, attr, str(uuid.uuid4()), nullable)

@pytest.mark.parametrize("attr, nullable", [
    ("start_time", False),
    ("status_change_datetime", True)
])
def test_set_datetime(recording: models.Recording, attr: str, nullable: bool):
    test_datetime = datetime.datetime(2020,8,21,2,54,22)
    test_datetime = test_datetime - datetime.timedelta(seconds = 5)
    test_datetime_string = test_datetime.strftime("%Y-%m-%dT%H:%M:%S")
    setattr(recording, attr, test_datetime)
    assert common.equate_timestamps(getattr(recording, attr), test_datetime)
    test_datetime = test_datetime - datetime.timedelta(seconds = 5)
    test_datetime_string = test_datetime.strftime("%Y-%m-%dT%H:%M:%S")
    setattr(recording, attr, test_datetime_string)
    assert common.equate_timestamps(getattr(recording, attr), test_datetime)
    test_datetime = datetime.datetime(2021,8,21,2,54)
    test_datetime_string = test_datetime.strftime("%Y-%m-%dT%H:%M")
    setattr(recording, attr, test_datetime_string)
    assert common.equate_timestamps(getattr(recording, attr), test_datetime)

@pytest.mark.parametrize("attr", [
    "row_start",
    "created_datetime"
])
def test_set_reject(recording: models.Recording, attr: str):
    with pytest.raises(exception_handler.CriticalException):
        setattr(recording, attr, "Test")

@pytest.mark.parametrize("form", [
    ({
        'Irrelevant_Field': "",
    }), ])
def test_insert_or_update_attribute_error(recording: models.Recording, form):
    with pytest.raises(AttributeError):
        recording._insert_or_update(form = form, new = False)

@pytest.mark.parametrize("form", [
    ({
        'start_time': "2020-10-08T10:15:22",
        'status': "In Progress",
        'notes': "",
    }),
    ({
        'start_time': "2020-10-08T10:15:22",
    }), ])
def test_insert_or_update(recording: models.Recording, form):
    recording_old = copy.deepcopy(recording)
    recording._insert_or_update(form = form, new = False)
    assert common.equate_timestamps(recording.start_time, datetime.datetime.strptime(form['start_time'], "%Y-%m-%dT%H:%M:%S"))
    if 'status' in form: assert recording.status == form['status'] if 'status' in form else True
    if 'notes' in form: assert common.create_assertion(recording.notes, recording_old.notes, form['notes'] if 'notes' in form else "") if 'notes' in form else True

def test_unique_name(recording: models.Recording):
    assert recording.unique_name == recording.encounter.unique_name + ', Recording: ' + str(recording.start_time)

def test_update_status_override_unassigned(recording: models.Recording):
    recording._update_status(override="Unassigned")
    assert recording.is_unassigned()

def test_update_status_override_in_progress(recording: models.Recording):
    recording._update_status(override="In Progress")
    assert recording.is_in_progress()
    assert recording.status_change_datetime is not None

def test_update_status_override_awaiting_review(recording: models.Recording):
    recording._update_status(override="Awaiting Review")
    assert recording.is_awaiting_review()
    assert recording.status_change_datetime is not None

def test_update_status_override_reviewed(recording: models.Recording):
    recording._update_status(override="Reviewed")
    assert recording.is_reviewed()
    assert recording.status_change_datetime is not None

def test_update_status_wrong(recording: models.Recording):
    with pytest.raises(exception_handler.ValidationError):
        recording._update_status(override="this-is-not-a-valid-status")

def test_update_status_unassigned(recording: models.Recording):
    recording._update_status(assignments=[])
    assert recording.status == "Unassigned"
    assert recording.status_change_datetime is None # Status hasn't changed from the default yet

def test_update_status_unassigned_2(recording: models.Recording):
    recording.status = "In Progress"
    recording._update_status(assignments=[])
    assert recording.status == "Unassigned"
    assert recording.status_change_datetime is not None

def test_update_status_unassigned_3(recording: models.Recording):
    recording.status = "Awaiting Review"
    recording._update_status(assignments=[])
    assert recording.status == "Unassigned"
    assert recording.status_change_datetime is not None

def test_update_status_in_progress(recording: models.Recording):
    recording._update_status(assignments=[factories.AssignmentFactory.create()])
    # With one assignment incomplete
    assert recording.status == "In Progress"
    assert recording.status_change_datetime is not None

def test_update_status_in_progress_2(recording: models.Recording):
    assignment1 = factories.AssignmentFactory.create()
    assignment2 = factories.AssignmentFactory.create()
    assignment2.completed_flag = True
    recording._update_status(assignments=[assignment1, assignment2])
    # With one assignment complete and one not complete
    assert recording.status == "In Progress"
    assert recording.status_change_datetime is not None

def test_update_status_awaiting_review(recording: models.Recording):
    assignment = factories.AssignmentFactory.create()
    assignment.completed_flag = True
    recording._update_status(assignments=[assignment])
    # With all assignments complete
    assert recording.status == "Awaiting Review"
    assert recording.status_change_datetime is not None

def test_update_status_reviewed_does_not_change(recording: models.Recording):
    recording.status = "Reviewed"
    recording._update_status(assignments=[])
    assert recording.is_reviewed()
    assert recording.status_change_datetime is None

def test_update_status_on_hold_does_not_change(recording: models.Recording):
    recording.status = "On Hold"
    recording._update_status(assignments=[])
    assert recording.is_on_hold()
    assert recording.status_change_datetime is None

def test_relative_directory(recording: models.Recording):
    for c in common.INVALID_CHARACTERS + ["_"]:
        recording.encounter = factories.EncounterFactory.create()
        recording.encounter.species.species_name = f"Test{c}Species"
        recording.encounter.encounter_name = f"Test{c}Encounter"
        recording.encounter.location = f"Test{c}Location"
        recording.start_time = datetime.datetime(2020,8,21,2,54,22)
        assert recording.relative_directory == os.path.join(f"Species-Test_Species", f"Location-Test_Location", f"Encounter-Test_Encounter",f"Recording-20200821T025422")

def test_relative_directory_exception(recording: models.Recording):
    recording.encounter = None
    with pytest.raises(exception_handler.CriticalException):
        recording.relative_directory

def test_recording_file_name(recording: models.Recording):
    for c in common.INVALID_CHARACTERS + ["_"]:
        recording.encounter.species.species_name = f"Test{c}Species"
        recording.encounter.encounter_name = f"Test{c}Encounter"
        recording.encounter.location = f"Test{c}Location"
        recording.start_time = datetime.datetime(2020,8,21,2,54,22)
        assert recording.recording_file_name == f"Rec-Test_Species-Test_Location-Test_Encounter-20200821T025422"

def test_selection_table_file_name(recording: models.Recording):
    for c in common.INVALID_CHARACTERS + ["_"]:
        species = recording.encounter.species
        species.species_name = f"Test{c}Species"
        recording.encounter.encounter_name = f"Test{c}Encounter"
        recording.encounter.location = f"Test{c}Location"
        recording.start_time = datetime.datetime(2020,8,21,2,54,22)
        assert recording.selection_table_file_name == f"SelTable-Test_Species-Test_Location-Test_Encounter-20200821T025422"

def test_ensure_selection_table_file_name_has_no_invalid_characters(recording: models.Recording):
    recording.encounter.species.species_name = f"TestSpecies" + "".join(common.INVALID_CHARACTERS)
    recording.encounter.encounter_name = f"TestEncounter" + "".join(common.INVALID_CHARACTERS)
    recording.encounter.location = f"TestLocation" + "".join(common.INVALID_CHARACTERS)
    recording.start_time = datetime.datetime(2020,8,21,2,54,22)
    for c in recording.selection_table_file_name:
        assert c not in common.INVALID_CHARACTERS

# NOTE: there is more rigorous testing of inserting into selection tables in the Selection module

def test_selection_table_apply_empty_dataframe(recording):
    dataframe = pd.DataFrame()
    selections = {}
    with pytest.raises(exception_handler.WarningException) as exc_info:
        recording._selection_table_apply(dataframe)

def test_selection_table_apply_missing_selection_column(recording):
    dataframe = pd.DataFrame({'other_column': [1, 2, 3]})
    selections = {}
    with pytest.raises(exception_handler.WarningException) as exc_info:
        recording._selection_table_apply(dataframe)

def test_selection_table_apply_missing_other_columns(recording: models.Recording):
    dataframe = pd.DataFrame({'Selection': [1, 2, 3]})
    selections = {}
    with pytest.raises(exception_handler.WarningException) as exc_info:
        recording._selection_table_apply(dataframe)

def test_selection_table_apply_new_selections(recording):
    dataframe = pd.DataFrame({'Selection': [1, 2, 3], 'View': ["1", "2", "3"], 'Channel': ["1", "2", "3"], 'Begin Time (s)': [1.1, 2.2, 3.3], 'End Time (s)': [1.1, 2.2, 3.3], 'Low Freq (Hz)': [1.1, 2.2, 3.3], 'High Freq (Hz)': [1.1, 2.2, 3.3], 'Annotation': ["Y", "N", "M"]})
    selections = {}
    new_selections = recording._selection_table_apply(dataframe)
    assert len(new_selections) == 3
    for selection in new_selections:
        assert isinstance(selection, models.Selection)
        assert selection.recording.id == recording.id