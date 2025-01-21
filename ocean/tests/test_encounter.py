# Standard library imports
import copy
import uuid
import os

# Third-party libraries
import pytest

# Local application imports
from . import factories
from . import common
from ..app import models
from ..app import exception_handler
UUID_TEST = uuid.uuid4()
EMPTY_CHARACTERS = common.EMPTY_CHARACTERS

@pytest.fixture
def encounter():
    return factories.EncounterFactory.create()

@pytest.mark.parametrize("attr, value, expected", [
    ("encounter_name", "TestName", "TestName"),
    ("encounter_name", " TestName", "TestName"),
    ("encounter_name", "TestName ", "TestName"),
    ("encounter_name", " Test Name ", "Test Name"),
    ("location", "TestName", "TestName"),
    ("location", " TestName", "TestName"),
    ("location", "TestName ", "TestName"),
    ("location", " Test Name ", "Test Name"),
    ("project", "TestName", "TestName"),
    ("project", " TestName", "TestName"),
    ("project", "TestName ", "TestName"),
    ("project", " Test Name ", "Test Name"),
    ("latitude", 1.6, 1.6),
    ("latitude", -50, -50),
    ("latitude", "1.6", 1.6),
    ("latitude", 0, 0),
    ("latitude", "1.613251", 1.613251),
    ("latitude", "0.00", 0),
    ("latitude", "", None),
    ("latitude", " ", None),
    ("latitude", None, None),
    ("longitude", 1.6, 1.6),
    ("longitude", -50, -50),
    ("longitude", "1.6", 1.6),
    ("longitude", 0, 0),
    ("longitude", "1.613251", 1.613251),
    ("longitude", "0.00", 0),
    ("longitude", "", None),
    ("longitude", " ", None),
    ("longitude", None, None),
    ("notes", "TestName", "TestName"),
    ("notes", " TestName\nHello\n\tThis is a new line.", "TestName\nHello\n\tThis is a new line."),
    ("notes", "TestName\nHello\n\tThis is a new line. ", "TestName\nHello\n\tThis is a new line."),
    ("notes", "TestName\nHello\n\tThis is a new line.", "TestName\nHello\n\tThis is a new line."),
    ("file_timezone", -100, -100),
    ("file_timezone", 0, 0),
    ("file_timezone", 50.0, 50),
    ("file_timezone", 100.8, 100),
    ("file_timezone", "-100", -100),
    ("file_timezone", "0", 0),
    ("file_timezone", "50.0", 50),
    ("file_timezone", "100.8", 100),
    ("local_timezone", -100, -100),
    ("local_timezone", 0, 0),
    ("local_timezone", 50.0, 50),
    ("local_timezone", 100.8, 100),
    ("local_timezone", "-100", -100),
    ("local_timezone", "0", 0),
    ("local_timezone", "50.0", 50),
    ("local_timezone", "100.8", 100)
])
def test_set_attribute(encounter: models.Encounter, attr: str, value, expected):
    common.test_set_attribute(encounter, attr, value, expected)

@pytest.mark.parametrize("attr, value", [
    ("encounter_name", 1),
    ("encounter_name", None),
    ("encounter_name", ""),
    ("encounter_name", "   "),
    ("location", 1),
    ("location", None),
    ("location", ""),
    ("location", "   "),
    ("project", 1),
    ("project", None),
    ("project", ""),
    ("project", "   "),
    ("species_id", "this-is-not-a-uuid"),
    ("species_id", 1),
    ("species_id", None),
    ("species_id", ""),
    ("species_id", "   "),
    ("data_source_id", "this-is-not-a-uuid"),
    ("data_source_id", 1),
    ("recording_platform_id", "this-is-not-a-uuid"),
    ("recording_platform_id", 1),
    ("updated_by_id", "this-is-not-a-uuid"),
    ("updated_by_id", 1)
])
def test_set_attribute_validation_error(encounter: models.Encounter, attr: str, value):
    common.test_set_attribute_validation_error(encounter, attr, value)

@pytest.mark.parametrize("attr, nullable", [
    ("species_id", False),
    ("data_source_id", True),
    ("recording_platform_id", True),
    ("updated_by_id", True)
])
def test_uuid(encounter: models.Encounter, attr: str, nullable: bool):
    common.validate_uuid(encounter, attr, str(uuid.uuid4()), nullable)

@pytest.mark.parametrize("form", [
    ({
        'encounter_name': "TestName",
        'location': "TestLocation",
        'project': "TestProject",
        'species_id': str(uuid.uuid4()),
        'latitude': "14.3",
        'longitude': "15.2",
        'data_source_id': str(uuid.uuid4()),
        'recording_platform_id': str(uuid.uuid4()),
        'notes': "Test Notes",
        'file_timezone': "200",
        'local_timezone': "-50"
    }),
    ({
        'encounter_name': "TestName",
        'location': "TestLocation",
        'project': "TestProject",
        'species_id': str(uuid.uuid4()),
        'latitude': "",
        'longitude': "",
        'data_source_id': "",
        'recording_platform_id': "",
        'notes': "",
        'file_timezone': "",
        'local_timezone': ""
    }),
    ({
        'encounter_name': "TestName",
        'location': "TestLocation",
        'project': "TestProject",
        'species_id': str(uuid.uuid4()),
    }) ])
def test_insert_or_update(encounter: models.Encounter, form):
    encounter_old = copy.deepcopy(encounter)
    encounter._insert_or_update(form = form, new = False)
    assert encounter.encounter_name == form['encounter_name']
    assert encounter.location == form['location']
    assert encounter.project == form['project']
    assert encounter.species_id == uuid.UUID(form['species_id'])
    assert common.create_assertion(encounter.latitude, encounter_old.latitude, float(form['latitude']) if ('latitude' in form and form['latitude']) else None)
    assert common.create_assertion(encounter.longitude, encounter_old.longitude, float(form['longitude']) if ('longitude' in form and form['longitude']) else None)
    assert common.create_assertion(encounter.notes, encounter_old.notes, form['notes'] if 'notes' in form else "")
    assert common.create_assertion(encounter.data_source_id, encounter_old.data_source_id, uuid.UUID(form['data_source_id']) if ('data_source_id' in form and form['data_source_id']) else None)
    assert common.create_assertion(encounter.recording_platform_id, encounter_old.recording_platform_id, uuid.UUID(form['recording_platform_id']) if ('recording_platform_id' in form and form['recording_platform_id']) else None)
    assert common.create_assertion(encounter.file_timezone, encounter_old.file_timezone, int(form['file_timezone']) if ('file_timezone' in form and form['file_timezone']) else None)
    assert common.create_assertion(encounter.local_timezone, encounter_old.local_timezone, int(form['local_timezone']) if ('local_timezone' in form and form['local_timezone']) else None)

@pytest.mark.parametrize("form", [
    ({
        'location': "TestLocation",
        'project': "TestProject",
        'species_id': str(uuid.uuid4()),
    }),
    ({
        'encounter_name': "TestName",
        'project': "TestProject",
        'species_id': str(uuid.uuid4()),
    }),
    ({
        'encounter_name': "TestName",
        'location': "TestLocation",
        'species_id': str(uuid.uuid4()),
    }),
    ({
        'encounter_name': "TestName",
        'location': "TestLocation",
        'project': "TestProject",
    }), ])
def test_insert_or_update_attribute_error(encounter: models.Encounter, form):
    with pytest.raises(AttributeError):
        encounter._insert_or_update(form = form, new = False)


def test_relative_directory(encounter: models.Encounter):
    encounter.species.scientific_name = "TestSpecies"
    encounter.encounter_name = "TestEncounter"
    encounter.location = "TestLocation"
    assert encounter.relative_directory == os.path.join("Species-TestSpecies", "Location-TestLocation", "Encounter-TestEncounter")

def test_relative_directory_invalid_characters(encounter: models.Encounter):
    for c in common.INVALID_CHARACTERS:
        encounter.species.scientific_name = f"Test{c}Species"
        encounter.encounter_name = f"Test{c}Encounter"
        encounter.location = f"Test{c}Location"
        assert encounter.relative_directory == os.path.join(f"Species-Test_Species", f"Location-Test_Location", f"Encounter-Test_Encounter")

def test_folder_name(encounter: models.Encounter):
    encounter.encounter_name = "TestEncounter"
    assert encounter.folder_name == "Encounter-TestEncounter"

def test_folder_name_invalid_characters(encounter: models.Encounter):
    for c in common.INVALID_CHARACTERS:
        encounter.encounter_name = f"Test{c}Encounter"
        assert encounter.folder_name == f"Encounter-Test_Encounter"

def test_location_folder_name(encounter: models.Encounter):
    encounter.location = "TestLocation"
    assert encounter.location_folder_name == "Location-TestLocation"

def test_location_folder_name_invalid_characters(encounter: models.Encounter):
    for c in common.INVALID_CHARACTERS:
        encounter.location = f"Test{c}Location"
        assert encounter.location_folder_name == f"Location-Test_Location"