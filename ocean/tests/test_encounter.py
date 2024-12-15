import pytest
from . import factories
from .factories import session
from ..app.logger import logger

EMPTY_CHARACTERS = ["", " ", "\n", "\t"]

@pytest.fixture
def encounter():
    return factories.EncounterFactory.create()

def test_hasattr_updated_by_id(encounter):
    """Test if the Encounter object has the updated_by_id attribute"""
    assert hasattr(encounter, "set_updated_by_id") == True
    
def test_hasattr_update_call(encounter):
    assert hasattr(encounter, "update_call") == True
    
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
        with pytest.raises(ValueError):
            encounter.set_encounter_name(c)
    
def test_set_location(encounter):
    encounter.set_location("Test")
    assert encounter.location == "Test"

def test_set_location_invalid(encounter):
    for c in EMPTY_CHARACTERS:
        with pytest.raises(ValueError):
            encounter.set_location(c)

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