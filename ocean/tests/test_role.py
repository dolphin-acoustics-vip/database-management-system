import pytest
import uuid
from . import factories
from . import common
from ..app import exception_handler
from ..app import models

@pytest.fixture
def role():
    return factories.RoleFactory()


@pytest.mark.parametrize("attr, value, expected", [
    ("id", "1", 1),
    ("id", 1, 1),
    ("name", "TestName ", "TestName"),
    ("name", " Test Name ", "Test Name"),
])
def test_set_attribute(role: models.Role, attr: str, value, expected):
    common.test_set_attribute(role, attr, value, expected)

@pytest.mark.parametrize("attr, value", [
    ("id", None),
    ("id", ""),
    ("id", "   "),
    ("name", None),
    ("name", ""),
    ("name", "   ")
])
def test_set_attribute_validation_error(role: models.Role, attr: str, value):
    common.test_set_attribute_validation_error(role, attr, value)