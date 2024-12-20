# Standard library imports
import uuid
import datetime
import os

# Third-party libraries
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


ENCOUNTER_NAME = "EncounterName"
ENCOUNTER_LOCATION = "EncounterLocation"
ENCOUNTER_PROJECT = "EncounterProject"
RECORDING_START_TIME = datetime.datetime(2020,8,21,2,54,22)
SPECIES_NAME = "SpeciesName"

@pytest.fixture
def recording_with_encounter():
    recording = factories.RecordingFactory.create()
    encounter = factories.EncounterFactory.create()
    species = factories.SpeciesFactory.create()
    species.species_name = SPECIES_NAME
    encounter.encounter_name = ENCOUNTER_NAME
    encounter.location = ENCOUNTER_LOCATION
    encounter.project = ENCOUNTER_PROJECT
    encounter.species = species
    recording.encounter = encounter
    recording.start_time = RECORDING_START_TIME
    return recording

def test_hasattr_updated_by_id(recording: models.Recording):
    """Test if the Encounter object has the updated_by_id attribute"""
    assert hasattr(recording, "set_updated_by_id") == True
    
def test_hasattr_update_call(recording: models.Recording):
    assert hasattr(recording, "update_call") == True

def test_hasattr_delete_children(recording: models.Recording):
    assert hasattr(recording, "delete_children") == True    

def test_hasattr_row_start(recording: models.Recording):
    assert hasattr(recording, "row_start")
    assert hasattr(recording, "get_row_start")
    assert hasattr(recording, "get_row_start_pretty")

def test_hasattr_relative_directory(recording: models.Recording):
    assert hasattr(recording, "generate_relative_directory")

def test_hasattr_created_datetime(recording: models.Recording):
    assert hasattr(recording, "created_datetime")
    assert hasattr(recording, "get_created_datetime")
    assert hasattr(recording, "get_created_datetime_pretty")

def test_hasattr_getters(recording: models.Recording):
    assert hasattr(recording, "get_start_time")
    assert hasattr(recording, "get_recording_file_id")
    assert hasattr(recording, "get_recording_file")
    assert hasattr(recording, "get_encounter_id")
    assert hasattr(recording, "get_encounter")
    assert hasattr(recording, "get_status")
    assert hasattr(recording, "get_status_change_datetime")
    assert hasattr(recording, "get_status_change_datetime_pretty")
    assert hasattr(recording, "get_notes")

def test_hasattr_setters(recording: models.Recording):
    assert hasattr(recording, "set_start_time")
    assert hasattr(recording, "set_recording_file_id")
    assert hasattr(recording, "set_recording_file")
    assert hasattr(recording, "set_encounter_id")
    assert hasattr(recording, "set_encounter")
    assert hasattr(recording, "set_status")
    assert hasattr(recording, "set_status_change_datetime")
    assert hasattr(recording, "set_notes")

def test_hasattr_other_methods(recording: models.Recording):
    # Testing a number of methods which cannot be unit tested.
    # Effectively enforcing a schema.
    # NOTE: these methods will be tested in integration testing.
    assert hasattr(recording, "update_status")
    assert hasattr(recording, "set_status_on_hold")
    assert hasattr(recording, "set_status_reviewed")
    assert hasattr(recording, "get_number_of_selections")
    assert hasattr(recording, "get_number_of_contours")
    assert hasattr(recording, "find_missing_selections")
    assert hasattr(recording, "export_selection_table")
    assert hasattr(recording, "load_and_validate_selection_table")
    assert hasattr(recording, "unpack_selection_table")

def test_get_unique_name(recording_with_encounter: models.Recording):
    # Note the default delimiter is dash (-)
    assert recording_with_encounter.get_unique_name() == f"Encounter: {ENCOUNTER_NAME}-{ENCOUNTER_LOCATION}-{ENCOUNTER_PROJECT}, Recording: {utils.pretty_date(RECORDING_START_TIME)}"

def test_get_unique_name_delimiter(recording_with_encounter: models.Recording):
    assert recording_with_encounter.get_unique_name() == f"Encounter: {ENCOUNTER_NAME}-{ENCOUNTER_LOCATION}-{ENCOUNTER_PROJECT}, Recording: {utils.pretty_date(RECORDING_START_TIME)}"
    
def test_set_start_time(recording: models.Recording):
    timestamp = datetime.datetime.now()
    for f in DATE_FORMAT:
        time_string, timestamp = common.parse_timestamp(timestamp, f)
        recording.set_start_time(timestamp)
        
        assert type(recording.start_time) == datetime.datetime
        assert recording.start_time.tzinfo is not None # Check that the set value contains timezone information
        assert common.equate_timestamps(timestamp, recording.start_time) == True

def test_set_start_time_str(recording: models.Recording):
    timestamp = datetime.datetime.now()
    for f in DATE_FORMAT:
        time_string, timestamp = common.parse_timestamp(timestamp, f)
        recording.set_start_time(time_string)
        assert type(recording.start_time) == datetime.datetime
        assert recording.start_time.tzinfo is not None # Check that the set value contains timezone information
        assert common.equate_timestamps(timestamp, recording.start_time) == True

def test_set_start_time_str_incorrect_format(recording: models.Recording):
    with pytest.raises(exception_handler.WarningException):
        recording.set_start_time("this-is-not-a-date")
 
@pytest.mark.parametrize("c", EMPTY_CHARACTERS)
def test_set_start_time_empty(recording: models.Recording, c: str):
    with pytest.raises(exception_handler.WarningException):
        recording.set_start_time(c)
        
def test_remove_recording_file(recording: models.Recording):
    recording.recording_file_id = uuid.uuid4()
    assert recording.remove_recording_file() == None
    assert recording.recording_file_id == None
    assert recording.recording_file == None
    
    recording_file = factories.FileFactory.create()
    recording.recording_file = recording_file
    assert recording.remove_recording_file() == recording_file
    assert recording.recording_file_id == None
    assert recording.recording_file == None
    
    recording.recording_file_id = uuid.uuid4()
    recording_file = factories.FileFactory.create()
    recording.recording_file = recording_file
    assert recording.remove_recording_file() == recording_file
    assert recording.recording_file_id == None
    assert recording.recording_file == None
        
def test_set_recording_file_id(recording: models.Recording):
    recording_file_id = uuid.uuid4()
    recording.set_recording_file_id(recording_file_id)
    assert recording.recording_file_id == recording_file_id
    
@pytest.mark.parametrize("c", EMPTY_CHARACTERS)
def test_set_recording_file_id_none(recording: models.Recording, c: str):
    with pytest.raises(exception_handler.WarningException):
        recording.set_recording_file_id(c)

def test_set_recording_file_id_wrong_type(recording: models.Recording):
    with pytest.raises(exception_handler.WarningException):
        recording.set_recording_file_id("this-is-not-a-uuid")

def test_set_recording_file_id_already_exists(recording: models.Recording):
    recording.set_recording_file_id(uuid.uuid4())
    with pytest.raises(ValueError):
        recording.set_recording_file_id(uuid.uuid4())

def test_set_recording_file(recording: models.Recording):
    recording_file = factories.FileFactory.create()
    recording.set_recording_file(recording_file)
    assert recording.recording_file == recording_file

def test_set_recording_file_none(recording: models.Recording):
    with pytest.raises(exception_handler.WarningException):
        recording.set_recording_file(None)

def test_set_recording_file_wrong_type(recording: models.Recording):
    with pytest.raises(ValueError):
        recording.set_recording_file(factories.SpeciesFactory.create())

def test_set_recording_file_already_exists(recording: models.Recording):
    recording.set_recording_file(factories.FileFactory.create())
    with pytest.raises(ValueError):
        recording.set_recording_file(factories.FileFactory.create())

def test_set_encounter_id(recording: models.Recording):
    encounter_id = uuid.uuid4()
    recording.set_encounter_id(encounter_id)
    assert recording.encounter_id == encounter_id
    
@pytest.mark.parametrize("c", EMPTY_CHARACTERS)
def test_set_encounter_id_none(recording: models.Recording, c: str):
    with pytest.raises(exception_handler.WarningException):
        recording.set_encounter_id(c)

def test_set_encounter_id_wrong_type(recording: models.Recording):
    with pytest.raises(exception_handler.WarningException):
        recording.set_encounter_id("this-is-not-a-uuid")

def test_set_encounter(recording: models.Recording):
    encounter = factories.EncounterFactory.create()
    recording.set_encounter(encounter)
    assert recording.encounter == encounter

def test_set_encounter_none(recording: models.Recording):
    with pytest.raises(exception_handler.WarningException):
        recording.set_encounter(None)

def test_set_encounter_wrong_type(recording: models.Recording):
    with pytest.raises(ValueError):
        recording.set_encounter(factories.SpeciesFactory.create())

def test_set_status(recording: models.Recording):
    recording.set_status("Unassigned")
    assert recording.status == "Unassigned"
    recording.set_status("unassigned")
    assert recording.status == "Unassigned"
    recording.set_status("In Progress")
    assert recording.status == "In Progress"
    recording.set_status("in progress")
    assert recording.status == "In Progress"
    recording.set_status("In progress")
    assert recording.status == "In Progress"
    recording.set_status("Awaiting Review")
    assert recording.status == "Awaiting Review"
    recording.set_status("awaiting review")
    assert recording.status == "Awaiting Review"
    recording.set_status("Awaiting review")
    assert recording.status == "Awaiting Review"
    recording.set_status("Reviewed")
    assert recording.status == "Reviewed"
    recording.set_status("reviewed")
    assert recording.status == "Reviewed"
    recording.set_status("On Hold")
    assert recording.status == "On Hold"
    recording.set_status("on hold")
    assert recording.status == "On Hold"
    recording.set_status("On hold")
    assert recording.status == "On Hold"
    
def test_set_status_changes_datetime(recording: models.Recording):
    for status in ["Unassigned", "In Progress", "Awaiting Review", "Reviewed", "On Hold"]:
        recording.set_status(status)
        assert recording.status_change_datetime is not None
        recording.status_change_datetime = None
        recording.status = None
    
def test_set_status_wrong(recording: models.Recording):
    with pytest.raises(exception_handler.WarningException):
        recording.set_status("this-is-not-a-valid-status")
    with pytest.raises(exception_handler.WarningException):
        recording.set_status(1) # Statuses are not integers

def test_set_status_change_datetime(recording: models.Recording):
    timestamp = datetime.datetime.now(datetime.timezone.utc)
    recording.set_status_change_datetime(timestamp)
    assert recording.status_change_datetime == timestamp

def test_set_status_change_datetime_str(recording: models.Recording):
    timestamp = datetime.datetime.now()
    for f in DATE_FORMAT:
        time_string, timestamp = common.parse_timestamp(timestamp, f)
        recording.set_status_change_datetime(time_string)
        assert type(recording.status_change_datetime) == datetime.datetime
        assert recording.status_change_datetime.tzinfo is not None # Check that the set value contains timezone information
        assert common.equate_timestamps(timestamp, recording.status_change_datetime) == True

def test_set_notes(recording: models.Recording):
    recording.set_notes("Test")
    assert recording.notes == "Test"

def test_set_notes_whitespace(recording: models.Recording):
    recording.set_notes("  Test \t")
    assert recording.notes == "Test"

def test_set_notes_multiple_lines(recording: models.Recording):
    recording.set_notes("Test\nTest")
    assert recording.notes == "Test\nTest"

@pytest.mark.parametrize("c", EMPTY_CHARACTERS)
def test_set_notes_empty(recording: models.Recording, c: str):
    recording.set_notes(c)
    assert recording.notes == None
        
def test_get_start_time(recording: models.Recording):
    timestamp = datetime.datetime.now(datetime.timezone.utc)
    recording.start_time = timestamp
    assert recording.get_start_time() == timestamp
    
def test_get_recording_file_id(recording: models.Recording):
    recording_file_id = uuid.uuid4()
    recording.recording_file_id = recording_file_id
    assert recording.get_recording_file_id() == recording_file_id
    recording_file_id = uuid.uuid4()
    recording.recording_file_id = recording_file_id.hex
    assert recording.get_recording_file_id() == recording_file_id
    recording.recording_file_id = None
    assert recording.get_recording_file_id() == None
    recording.recording_file_id = "not-a-uuid"
    with pytest.raises(exception_handler.WarningException):
        recording.get_recording_file_id()

def test_get_recording_file(recording: models.Recording):
    recording_file = factories.FileFactory.create()
    recording.recording_file = recording_file
    assert recording.get_recording_file() == recording_file
    recording.recording_file = None
    assert recording.get_recording_file() == None
    recording.recording_file = factories.SpeciesFactory.create()
    with pytest.raises(ValueError):
        recording.get_recording_file()

def test_get_encounter_id(recording: models.Recording):
    encounter_id = uuid.uuid4()
    recording.encounter_id = encounter_id
    assert recording.get_encounter_id() == encounter_id
    encounter_id = uuid.uuid4()
    recording.encounter_id = encounter_id.hex
    assert recording.get_encounter_id() == encounter_id
    recording.encounter_id = None
    assert recording.get_encounter_id() == None
    recording.encounter_id = "not-a-uuid"
    with pytest.raises(exception_handler.WarningException):
        recording.get_encounter_id()

def test_get_encounter(recording: models.Recording):
    encounter = factories.EncounterFactory.create()
    recording.encounter = encounter
    assert recording.get_encounter() == encounter
    recording.encounter = None
    assert recording.get_encounter() == None
    recording.encounter = factories.SpeciesFactory.create()
    with pytest.raises(ValueError):
        recording.get_encounter()
        
def test_get_status(recording: models.Recording):
    recording.status = "Awaiting Review"
    assert recording.get_status() == "Awaiting Review"

def test_get_status_change_datetime(recording: models.Recording):
    timestamp = datetime.datetime.now(datetime.timezone.utc)
    recording.status_change_datetime = timestamp
    assert recording.get_status_change_datetime() == timestamp
    recording.status_change_datetime = None
    assert recording.get_status_change_datetime() == None
    recording.status_change_datetime = "not-a-date"
    with pytest.raises(exception_handler.WarningException):
        recording.get_status_change_datetime()
    
def test_get_notes(recording: models.Recording):
    recording.notes = "Test Notes"
    assert recording.get_notes() == "Test Notes"
    recording.notes = None
    assert recording.get_notes() == ""
    recording.notes = ""
    assert recording.get_notes() == ""
    
def test_is_complete(recording: models.Recording):
    recording.status = "Unassigned"
    assert recording.is_complete() == False
    recording.status = "In Progress"
    assert recording.is_complete() == False
    recording.status = "Awaiting Review"
    assert recording.is_complete() == False
    recording.status = "Reviewed"
    assert recording.is_complete() == True
    recording.status = "On Hold"
    assert recording.is_complete() == False

def test_is_on_hold(recording: models.Recording):
    recording.status = "Unassigned"
    assert recording.is_on_hold() == False
    recording.status = "In Progress"
    assert recording.is_on_hold() == False
    recording.status = "Awaiting Review"
    assert recording.is_on_hold() == False
    recording.status = "Reviewed"
    assert recording.is_on_hold() == False
    recording.status = "On Hold"
    assert recording.is_on_hold() == True

def test_update_status(recording: models.Recording):
    # TODO (WITH ASSIGNMENT TESTING)
    pass

def test_generate_relative_directory(recording: models.Recording):
    recording.encounter.species.species_name = f"TestSpecies"
    recording.encounter.encounter_name = f"TestEncounter"
    recording.encounter.location = f"TestLocation"
    recording.start_time = datetime.datetime(2020,8,21,2,54,22)
    assert recording.generate_relative_directory() == os.path.join(f"Species-TestSpecies", f"Location-TestLocation", f"Encounter-TestEncounter",f"Recording-20200821T025422")

def test_generate_relative_directory_invalid_characters(recording: models.Recording):
    for c in ["/","\\","*","?","\"","<",">","|"," "]:
        recording.encounter.species.species_name = f"Test{c}Species"
        recording.encounter.encounter_name = f"Test{c}Encounter"
        recording.encounter.location = f"Test{c}Location"
        recording.start_time = datetime.datetime(2020,8,21,2,54,22)
        assert recording.generate_relative_directory() == os.path.join(f"Species-Test_Species", f"Location-Test_Location", f"Encounter-Test_Encounter",f"Recording-20200821T025422")

def test_generate_relative_directory_exception(recording: models.Recording):
    recording.encounter = None
    with pytest.raises(ValueError):
        recording.generate_relative_directory()

def test_generate_recording_file_name(recording: models.Recording):
    recording.encounter.species.species_name = f"TestSpecies"
    recording.encounter.encounter_name = f"TestEncounter"
    recording.encounter.location = f"TestLocation"
    recording.start_time = datetime.datetime(2020,8,21,2,54,22)
    assert recording.generate_recording_file_name() == f"Rec-TestSpecies-TestLocation-TestEncounter-20200821T025422"

def test_generate_recording_file_name_invalid_characters(recording: models.Recording):
    for c in ["/","\\","*","?","\"","<",">","|"," "]:
        recording.encounter.species.species_name = f"Test{c}Species"
        recording.encounter.encounter_name = f"Test{c}Encounter"
        recording.encounter.location = f"Test{c}Location"
        recording.start_time = datetime.datetime(2020,8,21,2,54,22)
        assert recording.generate_recording_file_name() == f"Rec-Test_Species-Test_Location-Test_Encounter-20200821T025422"

def test_ensure_generate_recording_file_name_has_no_invalid_characters(recording: models.Recording):
    recording.encounter.species.species_name = f"TestSpecies"
    recording.encounter.encounter_name = f"TestEncounter"
    recording.encounter.location = f"TestLocation"
    recording.start_time = datetime.datetime(2020,8,21,2,54,22)
    for c in recording.generate_recording_file_name():
        assert c not in ["/","\\","*","?","\"","<",">","|"," "]

def test_generate_selection_table_file_name(recording_with_encounter: models.Recording):
    recording = recording_with_encounter
    assert recording_with_encounter.generate_selection_table_file_name() == f"SelTable-{recording.encounter.species.species_name}-{recording.encounter.location}-{recording.encounter.encounter_name}-{filespace_handler.format_date_for_filespace(recording.start_time)}"
    
def test_generate_selection_table_file_name_invalid_characters(recording: models.Recording):
    for c in ["/","\\","*","?","\"","<",">","|"," "]:
        recording.encounter.species.species_name = f"Test{c}Species"
        recording.encounter.encounter_name = f"Test{c}Encounter"
        recording.encounter.location = f"Test{c}Location"
        recording.start_time = datetime.datetime(2020,8,21,2,54,22)
        assert recording.generate_selection_table_file_name() == f"SelTable-Test_Species-Test_Location-Test_Encounter-20200821T025422"

def test_ensure_generate_selection_table_file_name_has_no_invalid_characters(recording: models.Recording):
    recording.encounter.species.species_name = f"TestSpecies"
    recording.encounter.encounter_name = f"TestEncounter"
    recording.encounter.location = f"TestLocation"
    recording.start_time = datetime.datetime(2020,8,21,2,54,22)
    for c in recording.generate_selection_table_file_name():
        assert c not in ["/","\\","*","?","\"","<",">","|"," "]

# METHODS STILL TO UNIT TEST
# generate_relative_path_for_selections - THIS NEEDS TO MOVE TO THE Selection MODULE