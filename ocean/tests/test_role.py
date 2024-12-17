import pytest
import uuid
from . import factories
from . import common
from ..app import exception_handler
from ..app import models

@pytest.fixture
def role():
    return factories.RoleFactory()

def test_get_id(role: models.Role):
    role.id = 1
    assert role.get_id() == 1
    role.id = "1"
    assert role.get_id() == 1
    
def test_get_id_wrong_type(role: models.Role):
    role.id = "this-is-not-an-integer"
    with pytest.raises(ValueError):
        role.get_id()
        
def test_get_id_none(role: models.Role):
    role.id = None
    with pytest.raises(ValueError):
        role.get_id()

def test_get_name(role: models.Role):
    role.name = "System Administrator"
    assert role.get_name() == "System Administrator"

def test_get_name_none(role: models.Role):
    role.name = None
    assert role.get_name() == ""