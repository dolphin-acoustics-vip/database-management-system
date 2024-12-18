import pytest
import uuid
from . import factories
from . import common
from ..app import exception_handler
from ..app import models

EMPTY_CHARACTERS = common.EMPTY_CHARACTERS

@pytest.fixture
def user():
    return factories.UserFactory.create()

def test_hasattr_getters(user):
    assert hasattr(user, "get_login_id")
    assert hasattr(user, "get_name")
    assert hasattr(user, "get_role_id")
    assert hasattr(user, "get_role")
    assert hasattr(user, "get_is_active")
    assert hasattr(user, "get_expiry")
    assert hasattr(user, "get_expiry_pretty")

def test_hasattr_setters(user):
    assert hasattr(user, "set_login_id")
    assert hasattr(user, "set_name")
    assert hasattr(user, "set_role_id")
    assert hasattr(user, "set_role")
    assert hasattr(user, "set_expiry")


def test_set_role(user):
    role = factories.RoleFactory.create()
    user.set_role(role)
    assert user.role == role

def test_set_role_none(user):
    with pytest.raises(exception_handler.WarningException):
        user.set_role(None)

def test_set_role_wrong_type(user):
    with pytest.raises(ValueError):
        data_source = factories.DataSourceFactory.create()
        user.set_role(data_source)
    with pytest.raises(ValueError):
        user.set_role(1)
    with pytest.raises(ValueError):
        user.set_role("u8354")

def test_set_role_id(user):
    user.set_role_id(1)
    assert user.role_id == 1
    user.set_role_id("124")
    assert user.role_id == 124

@pytest.mark.parametrize("c", EMPTY_CHARACTERS)
def test_set_role_id_none(user, c):
    with pytest.raises(exception_handler.WarningException):
        user.set_role_id(c)

def test_set_role_id_wrong_type(user):
    with pytest.raises(exception_handler.WarningException):
        user.set_role_id(uuid.uuid4())
    with pytest.raises(exception_handler.WarningException):
        user.set_role_id("21581739as")
    with pytest.raises(exception_handler.WarningException):
        user.set_role_id(" ")
