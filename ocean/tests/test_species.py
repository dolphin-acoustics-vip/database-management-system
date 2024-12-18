import pytest
from . import factories

def test_hasattr_updated_by_id():
    """Test if the Species object has the updated_by_id attribute"""
    selection = factories.SpeciesFactory()
    assert hasattr(selection, "set_updated_by_id") == True

def test_updated_by_id():
    """Test that the """
    selection = factories.SpeciesFactory()
    assert selection.updated_by_id == None
    selection.set_updated_by_id("1")
    assert selection.updated_by_id == "1"
    selection.set_updated_by_id("15")
    assert selection.updated_by_id == "15"

def test_hasattr_update_call():
    selection = factories.SpeciesFactory()
    assert hasattr(selection, "update_call") == True

def test_hasattr_getters():
    selection = factories.SpeciesFactory()
    assert hasattr(selection, "get_species_name") == True
    assert hasattr(selection, "get_genus_name") == True
    assert hasattr(selection, "get_common_name") == True

def test_hasattr_setters():
    selection = factories.SpeciesFactory()
    assert hasattr(selection, "set_species_name") == True
    assert hasattr(selection, "set_genus_name") == True
    assert hasattr(selection, "set_common_name") == True

def test_get_species_name():
    selection = factories.SpeciesFactory(
        species_name = "Test Species"
    )
    assert selection.get_species_name() == "Test Species"

def test_get_genus_name():
    selection = factories.SpeciesFactory(
        genus_name = "Test Genus"
    )
    assert selection.get_genus_name() == "Test Genus"

def test_get_common_name():
    selection = factories.SpeciesFactory(
        common_name = "Test Common Name"
    )
    assert selection.get_common_name() == "Test Common Name"

def test_set_species_name():
    selection = factories.SpeciesFactory()
    selection.set_species_name("Test Species")
    assert selection.species_name == "Test Species"

def test_set_species_name_none():
    selection = factories.SpeciesFactory()
    with pytest.raises(ValueError):
        selection.set_species_name(None)

def test_set_species_name_empty():
    selection = factories.SpeciesFactory()
    with pytest.raises(ValueError):
        selection.set_species_name("")
    with pytest.raises(ValueError):
        selection.set_species_name(" ")
    with pytest.raises(ValueError):
        selection.set_species_name("\t")

def test_set_species_name_whitespace():
    selection = factories.SpeciesFactory()
    selection.set_species_name("  Test Species      ")
    assert selection.species_name == "Test Species"
    
def test_set_genus_name():
    selection = factories.SpeciesFactory()
    selection.set_genus_name("Test Genus")
    assert selection.genus_name == "Test Genus"

def test_set_genus_name_none():
    selection = factories.SpeciesFactory()
    selection.set_genus_name(None)
    assert selection.genus_name == None

def test_set_genus_name_empty():
    selection = factories.SpeciesFactory()
    selection.set_genus_name("")
    assert selection.genus_name == None
    selection.set_genus_name(" ")
    assert selection.genus_name == None

def test_set_genus_name_whitespace():
    selection = factories.SpeciesFactory()
    selection.set_genus_name("  Test Genus      ")
    assert selection.genus_name == "Test Genus"
    
def test_set_common_name():
    selection = factories.SpeciesFactory()
    selection.set_common_name("Test Common Name")
    assert selection.common_name == "Test Common Name"

def test_set_common_name_none():
    selection = factories.SpeciesFactory()
    selection.set_common_name(None)
    assert selection.common_name == None

def test_set_common_name_empty():
    selection = factories.SpeciesFactory()
    selection.set_common_name("")
    assert selection.common_name == None
    selection.set_common_name(" ")
    assert selection.common_name == None

def test_set_common_name_whitespace():
    selection = factories.SpeciesFactory()
    selection.set_common_name("  Test Common Name      ")
    assert selection.common_name == "Test Common Name"
