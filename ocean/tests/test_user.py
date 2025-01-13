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
    with pytest.raises(exception_handler.ValidationError):
        data_source = factories.DataSourceFactory.create()
        user.set_role(data_source)
    with pytest.raises(exception_handler.ValidationError):
        user.set_role(1)
    with pytest.raises(exception_handler.ValidationError):
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

def test_get_name(user):
    user.name = "name"
    assert user.get_name() == "name"

def test_set_name(user):
    user.set_name("name")
    assert user.name == "name"

def test_set_name_none(user):
    with pytest.raises(exception_handler.WarningException):
        user.set_name(None)
    with pytest.raises(exception_handler.WarningException):
        user.set_name("")

from ..app.models import User
from ..app.exception_handler import WarningException
from unittest.mock import Mock
from ..app.routes.routes_admin import update_or_insert_user

def test_update_or_insert_user_update_user():
    user = User(name="John Doe", role_id=1)
    request = Mock()
    request.form = {
        "name": "Jane Doe",
        "role": "2",
        "expiry": "2022-01-01"
    }
    update_or_insert_user(user, request)
    assert user.name == "Jane Doe"
    assert user.role_id == 2
    # assert user.expiry == "2022-01-01"

def test_update_or_insert_user_insert_user():
    user = None
    request = Mock()
    request.form = {
        "name": "John Doe",
        "role": "1",
        "expiry": "2022-01-01"
    }
    with pytest.raises(WarningException):
        update_or_insert_user(user, request)

def test_update_or_insert_user_login_id():
    user = User(name="John Doe", role_id=1)
    request = Mock()
    request.form = {
        "name": "Jane Doe",
        "role": "2",
        "expiry": "2022-01-01",
        "login_id": "johndoe"
    }
    update_or_insert_user(user, request)
    assert user.login_id == "johndoe"

# def test_update_or_insert_user_role_change_for_current_user():
#     user = User(name="John Doe", role_id=1)
#     request = Mock()
#     request.form = {
#         "name": "Jane Doe",
#         "role": "2",
#         "expiry": "2022-01-01"
#     }
#     with pytest.raises(WarningException):
#         update_or_insert_user(user, request)

# def test_update_or_insert_user_expiry_date_in_past_for_current_user():
#     user = User(name="John Doe", role_id=1)
#     request = Mock()
#     request.form = {
#         "name": "Jane Doe",
#         "role": "1",
#         "expiry": "2020-01-01"
#     }
#     with pytest.raises(WarningException):
#         update_or_insert_user(user, request)

def test_update_or_insert_user_is_active():
    user = User(name="John Doe", role_id=1)
    request = Mock()
    request.form = {
        "name": "Jane Doe",
        "role": "2",
        "expiry": "2022-01-01",
        "is_active": "on"
    }
    update_or_insert_user(user, request)
    assert user.is_active

def test_update_or_insert_user_is_active_not_checked():
    user = User(name="John Doe", role_id=1)
    request = Mock()
    request.form = {
        "name": "Jane Doe",
        "role": "2",
        "expiry": "2022-01-01"
    }
    update_or_insert_user(user, request)
    assert not user.is_active

# def test_update_or_insert_user_is_active_for_current_user():
#     user = User(name="John Doe", role_id=1)
#     request = Mock()
#     request.form = {
#         "name": "Jane Doe",
#         "role": "2",
#         "expiry": "2022-01-01",
#         "is_active": "off"
#     }
#     with pytest.raises(WarningException):
#         update_or_insert_user(user, request)