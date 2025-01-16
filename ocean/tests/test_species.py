import pytest
from pytest import fixture
from . import factories
from ..app import models
from ..app import exception_handler
import uuid
from . import common

EMPTY_CHARACTERS = common.EMPTY_CHARACTERS

@fixture
def species():
    return factories.SpeciesFactory.create()

def test_updated_by_id(species: models.Species):
    user_id = uuid.uuid4()
    species.updated_by_id = user_id
    assert species.updated_by_id == user_id

@pytest.mark.parametrize("c", EMPTY_CHARACTERS)
def test_set_updated_by_id_empty(species: models.Species, c: str):
    species.updated_by_id = c
    assert species.updated_by_id == None

def test_set_updated_by_id_wrong_type(species: models.Species):
    with pytest.raises(exception_handler.ValidationError):
        species.updated_by_id = "this-is-not-a-uuid"

@pytest.mark.parametrize("attr, value, expected", [
    ("species_name", "TestName", "TestName"),
    ("species_name", " TestName", "TestName"),
    ("species_name", "TestName ", "TestName"),
    ("species_name", " Test Name ", "Test Name"),
    ("genus_name", "TestName", "TestName"),
    ("genus_name", " TestName", "TestName"),
    ("genus_name", "TestName ", "TestName"),
    ("genus_name", " Test Name ", "Test Name"),
    ("genus_name", None, None),
    ("genus_name", "", None),
    ("genus_name", "  ", None),
    ("common_name", "TestName", "TestName"),
    ("common_name", " TestName", "TestName"),
    ("common_name", "TestName ", "TestName"),
    ("common_name", " Test Name ", "Test Name"),
    ("common_name", None, None),
    ("common_name", "", None),
    ("common_name", "  ", None)
])
def test_set_attribute(species: models.Species, attr: str, value, expected):
    setattr(species, attr, value)
    assert getattr(species, attr) == expected

@pytest.mark.parametrize("attr, value", [
    ("species_name", 1),
    ("species_name", None),
    ("species_name", ""),
    ("species_name", "   "),
    ("genus_name", 1),
    ("common_name", 1)
])
def test_validation_error(species: models.Species, attr: str, value):
    with pytest.raises(exception_handler.ValidationError):
        setattr(species, attr, value)


def test_to_dict(species: models.Species):
    expected = {
            'id': species.id,
            'species_name': species.species_name,
            'genus_name': species.genus_name,
            'common_name': species.common_name,
            'updated_by_id': species.updated_by_id,
        }
    assert expected == species._to_dict()