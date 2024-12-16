import pytest
from . import factories
from ..app import models

@pytest.fixture
def selection():
    return factories.SelectionFactory.create()

def test_hasattr_updated_by_id(selection: models.Selection):
    """Test if the Encounter object has the updated_by_id attribute"""
    assert hasattr(selection, "set_updated_by_id") == True
    
def test_hasattr_update_call(selection: models.Selection):
    assert hasattr(selection, "update_call") == True

def test_hasattr_delete_children(selection: models.Selection):
    assert hasattr(selection, "delete_children") == True    

def test_hasattr_row_start(selection: models.Selection):
    assert hasattr(selection, "row_start")
    assert hasattr(selection, "get_row_start")
    assert hasattr(selection, "get_row_start_pretty")

def test_hasattr_relative_directory(selection: models.Selection):
    assert hasattr(selection, "generate_relative_directory")

def test_hasattr_created_datetime(selection: models.Selection):
    assert hasattr(selection, "created_datetime")
    assert hasattr(selection, "get_created_datetime")
    assert hasattr(selection, "get_created_datetime_pretty")
