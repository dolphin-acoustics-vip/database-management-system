import pytest
import uuid
from . import factories
from . import common
from ..app import exception_handler
from ..app import models


from ..app.models import User
from unittest.mock import Mock
from ..app.routes.routes_admin import update_or_insert_user

EMPTY_CHARACTERS = common.EMPTY_CHARACTERS

@pytest.fixture
def user():
    return factories.UserFactory.create()

@pytest.fixture
def admin_user():
    return factories.UserFactory(name="Admin", role_id=1, login_id="admin@gmail.com")

def test_set_role(user):
    role = factories.RoleFactory.create()
    user.role = role
    assert user.role == role

def test_set_role_none(user):
    with pytest.raises(exception_handler.ValidationError):
        user.role = None

def test_set_role_wrong_type(user):
    with pytest.raises(exception_handler.ValidationError):
        data_source = factories.DataSourceFactory.create()
        user.role = data_source
    with pytest.raises(exception_handler.ValidationError):
        user.role = 1
    with pytest.raises(exception_handler.ValidationError):
        user.role = "u8354"

def test_set_role_id(user):
    user.role_id = 1
    assert user.role_id == 1
    user.role_id = "124"
    assert user.role_id == 124

@pytest.mark.parametrize("c", EMPTY_CHARACTERS)
def test_set_role_id_none(user, c):
    with pytest.raises(exception_handler.ValidationError):
        user.role_id = c

def test_set_role_id_wrong_type(user):
    with pytest.raises(exception_handler.ValidationError):
        user.role_id = uuid.uuid4()
    with pytest.raises(exception_handler.ValidationError):
        user.role_id = "21581739as"
    with pytest.raises(exception_handler.ValidationError):
        user.role_id = " "

@pytest.mark.parametrize("c", EMPTY_CHARACTERS)
def test_set_name_none(user, c):
    user.name = c
    assert user.name == None

def test_update_or_insert_user_update_user():
    user = User()
    request = Mock()
    request.form = {
        "name": "Jane Doe",
        "login_id": "johndoe@gmail.com",
        "role_id": "2",
        "expiry": "2022-01-01"
    }
    user.insert(request.form)
    assert user.name == "Jane Doe"
    assert user.role_id == 2
    assert user.login_id == "johndoe@gmail.com"

def test_insert_user_attribute_error():
    user = User()
    request = Mock()
    request.form = {
        "name": "John Doe",
        "role": "1",
        "expiry": "2022-01-01"
    }
    with pytest.raises(AttributeError):
        user.insert(request.form)

def test_update_user(user, admin_user):
    current_user = User(name="Admin", role_id=1, login_id="admin@gmail.com")
    
    user.login_id = "test@gmail.com"
    user.role_id = 1
    import datetime
    user.expiry = datetime.datetime.now() + datetime.timedelta(days=30)
    request = Mock()
    request.form = {
        "name": "Jane Doe",
        "role_id": "1",
        "expiry": "2026-01-01",
        "login_id": "johndoe@hotmail.com",
        "is_active":True
    }
    user.update(request.form, current_user)

def test_update_or_insert_user_login_id(user):
    current_user = factories.UserFactory(name="Admin", role_id=1, login_id="admin@gmail.com")
    user = User(name="John Doe", role_id=1, login_id="johndoe@gmail.com")
    request = Mock()
    request.form = {
        "name": "Jane Doe",
        "role_id": "2",
        "expiry": "2026-01-01",
        "login_id": "johndoe@hotmail.com",
        "is_active":True
    }
    user.update(request.form, current_user)
    assert user.login_id == "johndoe@gmail.com"

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
    user = User()
    request = Mock()
    request.form = {
        "login_id": "test@testmail.com",
        "name": "Jane Doe",
        "role_id": "2",
        "expiry": "2022-01-01",
        "is_active": "on"
    }
    user.insert(request.form)
    assert user.is_active

def test_update_or_insert_user_is_active_not_checked():
    user = User(name="John Doe", role_id=1)
    request = Mock()
    request.form = {
        "login_id": "test@testmail.com",
        "name": "Jane Doe",
        "role_id": "2",
        "expiry": "2022-01-01",
    }
    user.insert(request.form)
    assert not user.is_active

def test_update_role_current_user():
    user = User(name="John Doe", role_id=1)
    request = Mock()
    request.form = {
        "name": "Jane Doe",
        "role_id": "2",
        "expiry": "3000-01-01"
    }
    with pytest.raises(exception_handler.WarningException) as e:
        user.update(request.form, user)
        assert str(e).contains("You cannot change your own role")

def test_deactivate_current_user():
    user = User(name="John Doe", role_id=1, is_active=True)
    request = Mock()
    request.form = {
        "name": "Jane Doe",
        "role_id": "1",
        "expiry": "3000-01-01"
    }
    with pytest.raises(exception_handler.WarningException) as e:
        user.update(request.form, user)
        assert str(e).contains("You cannot deactivate yourself")