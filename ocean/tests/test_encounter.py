import uuid
import pytest
from . import factories
from .factories import session
from ..app.logger import logger
from ..app import exception_handler

EMPTY_CHARACTERS = ["", " ", "\n", "\t"]

@pytest.fixture
def encounter():
    return factories.EncounterFactory.create()

def test_hasattr_updated_by_id(encounter):
    """Test if the Encounter object has the updated_by_id attribute"""
    assert hasattr(encounter, "set_updated_by_id") == True
    
def test_hasattr_update_call(encounter):
    assert hasattr(encounter, "update_call") == True

def test_hasattr_delete_children(encounter):
    assert hasattr(encounter, "delete_children") == True    

def test_hasattr_getters(encounter):
    assert hasattr(encounter, "get_encounter_name") == True
    assert hasattr(encounter, "get_location") == True
    assert hasattr(encounter, "get_project") == True
    assert hasattr(encounter, "get_latitude") == True
    assert hasattr(encounter, "get_longitude") == True
    assert hasattr(encounter, "get_notes") == True
    assert hasattr(encounter, "get_file_timezone") == True
    assert hasattr(encounter, "get_local_timezone") == True 
    assert hasattr(encounter, "get_species_id") == True
    assert hasattr(encounter, "get_data_source_id") == True
    assert hasattr(encounter, "get_recording_platform_id") == True

def test_hasattr_setters(encounter):
    assert hasattr(encounter, "set_encounter_name") == True
    assert hasattr(encounter, "set_location") == True
    assert hasattr(encounter, "set_project") == True
    assert hasattr(encounter, "set_latitude") == True
    assert hasattr(encounter, "set_longitude") == True
    assert hasattr(encounter, "set_notes") == True
    assert hasattr(encounter, "set_file_timezone") == True
    assert hasattr(encounter, "set_local_timezone") == True 
    assert hasattr(encounter, "set_species") == True
    assert hasattr(encounter, "set_species_id") == True
    assert hasattr(encounter, "set_data_source") == True
    assert hasattr(encounter, "set_data_source_id") == True
    assert hasattr(encounter, "set_recording_platform") == True
    assert hasattr(encounter, "set_recording_platform_id") == True

def test_updated_by_id(encounter):
    """Test that the """
    assert encounter.updated_by_id == None
    encounter.set_updated_by_id("1")
    assert encounter.updated_by_id == "1"
    encounter.set_updated_by_id("15")
    assert encounter.updated_by_id == "15"

def test_set_encounter_name(encounter):
    encounter.set_encounter_name("Test")
    assert encounter.encounter_name == "Test"

def test_set_encounter_name_invalid(encounter):
    for c in EMPTY_CHARACTERS:
        with pytest.raises(exception_handler.WarningException):
            encounter.set_encounter_name(c)
    
def test_set_location(encounter):
    encounter.set_location("Test")
    assert encounter.location == "Test"

def test_set_location_invalid(encounter):
    for c in EMPTY_CHARACTERS:
        with pytest.raises(exception_handler.WarningException):
            encounter.set_location(c)

def test_set_project(encounter):
    encounter.set_project("Test")
    assert encounter.project == "Test"

def test_set_project_invalid(encounter):
    for c in EMPTY_CHARACTERS:
        with pytest.raises(exception_handler.WarningException):
            encounter.set_project(c)

def set_set_latitude(encounter):
    encounter.set_latitude(45.0)
    assert encounter.latitude == 45.0
    encounter.set_latitude(45)
    assert encounter.latitude == 45.0
    encounter.set_latitude("45")
    assert encounter.latitude == 45.0
    encounter.set_latitude("45.0")
    assert encounter.latitude == 45.0
    
def test_set_latitude_invalid_string(encounter):
    with pytest.raises(exception_handler.WarningException):
        encounter.set_latitude("invalid-latitude")

def test_set_latitude_out_of_range(encounter):
    with pytest.raises(exception_handler.WarningException):
        encounter.set_latitude(100.0)
        
def test_set_latitude_empty(encounter):
    encounter.set_latitude(None)
    assert encounter.latitude == None
    encounter.set_latitude("")
    assert encounter.latitude == None
    encounter.set_latitude(" ")
    assert encounter.latitude == None

def set_set_longitude(encounter):
    encounter.set_longitude(45.0)
    assert encounter.longitude == 45.0
    encounter.set_longitude(45)
    assert encounter.longitude == 45.0
    encounter.set_longitude("45")
    assert encounter.longitude == 45.0
    encounter.set_longitude("45.0")
    assert encounter.longitude == 45.0
    
def test_set_longitude_invalid_string(encounter):
    with pytest.raises(exception_handler.WarningException):
        encounter.set_longitude("invalid-longitude")

def test_set_longitude_out_of_range(encounter):
    with pytest.raises(exception_handler.WarningException):
        encounter.set_longitude(181.0)
    
def test_set_longitude_empty(encounter):
    encounter.set_longitude(None)
    assert encounter.longitude == None
    encounter.set_longitude("")
    assert encounter.longitude == None
    encounter.set_longitude(" ")
    assert encounter.longitude == None

def test_set_data_source(encounter):
    data_source = factories.DataSourceFactory.create()
    encounter.set_data_source(data_source)
    assert encounter.data_source == data_source

def test_set_data_source_id(encounter):
    data_source_id = uuid.uuid4().hex
    encounter.set_data_source_id(data_source_id)
    assert encounter.data_source_id == data_source_id

def test_set_recording_platform(encounter):
    recording_platform = factories.RecordingPlatformFactory.create()
    encounter.set_recording_platform(recording_platform)
    assert encounter.recording_platform == recording_platform

def test_set_recording_platform_id(encounter):
    recording_platform_id = uuid.uuid4().hex
    encounter.set_recording_platform_id(recording_platform_id)
    assert encounter.recording_platform_id == recording_platform_id

def test_set_notes(encounter):
    encounter.set_notes("Test")
    assert encounter.notes == "Test"

def test_set_notes_whitespace(encounter):
    encounter.set_notes("  Test \t")
    assert encounter.notes == "Test"

def test_set_notes_multiple_lines(encounter):
    encounter.set_notes("Test\nTest")
    assert encounter.notes == "Test\nTest"

def test_set_notes_empty(encounter):
    for c in EMPTY_CHARACTERS:
        encounter.set_notes(c)
        assert encounter.notes == None

def test_set_file_timezone(encounter):
    encounter.set_file_timezone(0)
    assert encounter.file_timezone == 0
    encounter.set_file_timezone(12)
    assert encounter.file_timezone == 12
    encounter.set_file_timezone(60)
    assert encounter.file_timezone == 60
    encounter.set_file_timezone(-60.3)
    assert encounter.file_timezone == -60

def test_set_file_timezone_string(encounter):
    encounter.set_file_timezone("0")
    assert encounter.file_timezone == 0
    encounter.set_file_timezone("12")
    assert encounter.file_timezone == 12
    encounter.set_file_timezone("60")
    assert encounter.file_timezone == 60
    encounter.set_file_timezone("-60.3")
    assert encounter.file_timezone == -60

def test_set_file_timezone_out_of_range(encounter):
    with pytest.raises(exception_handler.WarningException):
        encounter.set_file_timezone(1000)

def test_set_file_timezone_none(encounter):
    encounter.set_file_timezone(None)
    assert encounter.file_timezone == None
    encounter.set_file_timezone("")
    assert encounter.file_timezone == None
    encounter.set_file_timezone(" ")
    assert encounter.file_timezone == None

def test_set_file_timezone_wrong_type(encounter):
    with pytest.raises(exception_handler.WarningException):
        encounter.set_file_timezone("1.5f")
    with pytest.raises(exception_handler.WarningException):
        encounter.set_file_timezone("this-is-not-a timezone")
    with pytest.raises(exception_handler.WarningException):
        encounter.set_file_timezone(factories.SpeciesFactory.create())

def test_set_local_timezone(encounter):
    encounter.set_local_timezone(0)
    assert encounter.local_timezone == 0
    encounter.set_local_timezone(12)
    assert encounter.local_timezone == 12
    encounter.set_local_timezone(60)
    assert encounter.local_timezone == 60
    encounter.set_local_timezone(-60.3)
    assert encounter.local_timezone == -60

def test_set_local_timezone_string(encounter):
    encounter.set_local_timezone("0")
    assert encounter.local_timezone == 0
    encounter.set_local_timezone("12")
    assert encounter.local_timezone == 12
    encounter.set_local_timezone("60")
    assert encounter.local_timezone == 60
    encounter.set_local_timezone("-60.3")
    assert encounter.local_timezone == -60
    
def test_set_local_timezone_out_of_range(encounter):
    with pytest.raises(exception_handler.WarningException):
        encounter.set_local_timezone(-1000)

def test_set_local_timezone_none(encounter):
    encounter.set_local_timezone(None)
    assert encounter.local_timezone == None
    encounter.set_local_timezone("")
    assert encounter.local_timezone == None
    encounter.set_local_timezone(" ")
    assert encounter.local_timezone == None

def test_set_local_timezone_wrong_type(encounter):
    with pytest.raises(exception_handler.WarningException):
        encounter.set_local_timezone("1.5f")
    with pytest.raises(exception_handler.WarningException):
        encounter.set_local_timezone("this-is-not-a timezone")
    with pytest.raises(exception_handler.WarningException):
        encounter.set_local_timezone(factories.SpeciesFactory.create())

def test_set_species(encounter):
    species = factories.SpeciesFactory.create()
    encounter.set_species(species)
    assert encounter.species == species

def test_set_species_none(encounter):
    with pytest.raises(exception_handler.WarningException):
        encounter.set_species(None)

def test_set_species_wrong_type(encounter):
    with pytest.raises(exception_handler.WarningException):
        data_source = factories.DataSourceFactory.create()
        encounter.set_species(data_source)
    with pytest.raises(exception_handler.WarningException):
        encounter.set_species(1)
    with pytest.raises(exception_handler.WarningException):
        encounter.set_species("u8354")

def test_set_species_id(encounter):
    species_id = uuid.uuid4().hex
    encounter.set_species_id(species_id)
    assert encounter.species_id == species_id

def test_set_species_id_none(encounter):
    with pytest.raises(exception_handler.WarningException):
        encounter.set_species_id(None)

def test_set_species_id_wrong_type(encounter):
    with pytest.raises(exception_handler.WarningException):
        encounter.set_species_id(1)
    with pytest.raises(exception_handler.WarningException):
        encounter.set_species_id("21581739")

def test_set_data_source(encounter):
    data_source = factories.DataSourceFactory.create()
    encounter.set_data_source(data_source)
    assert encounter.data_source == data_source

def test_set_data_source_none(encounter):
    encounter.set_data_source(None)
    assert encounter.data_source == None

def test_set_data_source_wrong_type(encounter):
    with pytest.raises(exception_handler.WarningException):
        data_source = factories.SpeciesFactory.create()
        encounter.set_data_source(data_source)
    with pytest.raises(exception_handler.WarningException):
        encounter.set_data_source(1)
    with pytest.raises(exception_handler.WarningException):
        encounter.set_data_source("u8354")

def test_set_data_source_id(encounter):
    data_source_id = uuid.uuid4().hex
    encounter.set_data_source_id(data_source_id)
    assert encounter.data_source_id == data_source_id

def test_set_data_source_id_none(encounter):
    encounter.set_data_source_id(None)
    assert encounter.data_source_id == None

def test_set_data_source_id_wrong_type(encounter):
    with pytest.raises(exception_handler.WarningException):
        encounter.set_data_source_id(1)
    with pytest.raises(exception_handler.WarningException):
        encounter.set_data_source_id("21581739")

def test_set_recording_platform(encounter):
    recording_platform = factories.RecordingPlatformFactory.create()
    encounter.set_recording_platform(recording_platform)
    assert encounter.recording_platform == recording_platform

def test_set_recording_platform_none(encounter):
    encounter.set_recording_platform(None)
    assert encounter.recording_platform == None

def test_set_recording_platform_wrong_type(encounter):
    with pytest.raises(exception_handler.WarningException):
        recording_platform = factories.SpeciesFactory.create()
        encounter.set_recording_platform(recording_platform)
    with pytest.raises(exception_handler.WarningException):
        encounter.set_recording_platform(1)
    with pytest.raises(exception_handler.WarningException):
        encounter.set_recording_platform("u8354")

def test_set_recording_platform_id(encounter):
    recording_platform_id = uuid.uuid4().hex
    encounter.set_recording_platform_id(recording_platform_id)
    assert encounter.recording_platform_id == recording_platform_id

def test_set_recording_platform_id_none(encounter):
    encounter.set_recording_platform_id(None)
    assert encounter.recording_platform_id == None

def test_set_recording_platform_id_wrong_type(encounter):
    with pytest.raises(exception_handler.WarningException):
        encounter.set_recording_platform_id(1)
    with pytest.raises(exception_handler.WarningException):
        encounter.set_recording_platform_id("21581739")

def test_get_encounter_name(encounter):
    encounter.encounter_name = "Test Name"
    assert encounter.get_encounter_name() == "Test Name"
    encounter.encounter_name = None
    assert encounter.get_encounter_name() == ""
    encounter.encounter_name = ""
    assert encounter.get_encounter_name() == ""

def test_get_location(encounter):
    encounter.location = "Test Location"
    assert encounter.get_location() == "Test Location"
    encounter.location = None
    assert encounter.get_location() == ""
    encounter.location = ""
    assert encounter.get_location() == ""

def test_get_project(encounter):
    encounter.project = "Test Project"
    assert encounter.get_project() == "Test Project"
    encounter.project = None
    assert encounter.get_project() == ""
    encounter.project = ""
    assert encounter.get_project() == ""

def test_get_latitude(encounter):
    encounter.latitude = 1.0
    assert encounter.get_latitude() == 1.0
    encounter.latitude = 0
    assert encounter.get_latitude() == 0
    encounter.latitude = None
    assert encounter.get_latitude() == None
    encounter.latitude = "0"
    assert encounter.get_latitude() == 0
    encounter.latitude = "15.6"
    assert encounter.get_latitude() == 15.6
    # this should theoretically never happen if the proper setter is used
    encounter.latitude = "not-a-float"
    assert encounter.get_latitude() == None
    
def test_get_longitude(encounter):
    encounter.longitude = 1.0
    assert encounter.get_longitude() == 1.0
    encounter.longitude = 0
    assert encounter.get_longitude() == 0
    encounter.longitude = None
    assert encounter.get_longitude() == None
    encounter.longitude = "0"
    assert encounter.get_longitude() == 0
    encounter.longitude = "15.6"
    assert encounter.get_longitude() == 15.6
    # this should theoretically never happen if the proper setter is used
    encounter.longitude = "not-a-float"
    assert encounter.get_longitude() == None

def test_get_notes(encounter):
    encounter.notes = "Test Notes"
    assert encounter.get_notes() == "Test Notes"
    encounter.notes = None
    assert encounter.get_notes() == ""
    encounter.notes = ""
    assert encounter.get_notes() == ""

def test_get_file_timezone(encounter):
    encounter.file_timezone = 200
    assert encounter.get_file_timezone() == 200
    encounter.file_timezone = None
    assert encounter.get_file_timezone() == None
    encounter.file_timezone = "-200"
    assert encounter.get_file_timezone() == -200
    encounter.file_timezone = 0
    assert encounter.get_file_timezone() == 0

def test_get_local_timezone(encounter):
    encounter.local_timezone = 200
    assert encounter.get_local_timezone() == 200
    encounter.local_timezone = None
    assert encounter.get_local_timezone() == None
    encounter.local_timezone = "-200"
    assert encounter.get_local_timezone() == -200
    encounter.local_timezone = 0
    assert encounter.get_local_timezone() == 0

def test_get_species_id(encounter):
    species_id = uuid.uuid4()
    encounter.species_id = species_id
    assert encounter.get_species_id() == species_id
    species_id = uuid.uuid4()
    encounter.species_id = species_id.hex
    assert encounter.get_species_id() == species_id
    encounter.species_id = None
    assert encounter.get_species_id() == None
    encounter.species_id = "not-a-uuid"
    with pytest.raises(exception_handler.WarningException):
        encounter.get_species_id()

def test_get_data_source_id(encounter):
    data_source_id = uuid.uuid4()
    encounter.data_source_id = data_source_id
    assert encounter.get_data_source_id() == data_source_id
    data_source_id = uuid.uuid4()
    encounter.data_source_id = data_source_id.hex
    assert encounter.get_data_source_id() == data_source_id
    encounter.data_source_id = None
    assert encounter.get_data_source_id() == None
    encounter.data_source_id = "not-a-uuid"
    with pytest.raises(exception_handler.WarningException):
        encounter.get_data_source_id()

def test_get_recording_platform_id(encounter):
    recording_platform_id = uuid.uuid4()
    encounter.recording_platform_id = recording_platform_id
    assert encounter.get_recording_platform_id() == recording_platform_id
    recording_platform_id = uuid.uuid4()
    encounter.recording_platform_id = recording_platform_id.hex
    assert encounter.get_recording_platform_id() == recording_platform_id
    encounter.recording_platform_id = None
    assert encounter.get_recording_platform_id() == None
    encounter.recording_platform_id = "not-a-uuid"
    with pytest.raises(exception_handler.WarningException):
        encounter.get_recording_platform_id()



# def test_set_species(encounter, session):
#     species = factories.SpeciesFactory.create()
#     session.add(encounter)
#     session.add(species)
#     session.flush()
#     encounter.set_species(species)
#     session.commit()
#     assert str(encounter.species) == str(species)

# def test_set_species_id(encounter, session):
#     species = factories.SpeciesFactory.create()
#     session.add(species)
#     session.add(encounter)
#     session.flush()
#     encounter.set_species_id(species.id)
#     session.commit()
#     assert str(encounter.species) == str(species)
#     assert str(encounter.species_id) == str(species.id)