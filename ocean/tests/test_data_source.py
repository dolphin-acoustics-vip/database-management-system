import copy
import pytest
import uuid
from . import factories
from . import common
from ..app import exception_handler
from ..app import models

EMPTY_CHARACTERS = common.EMPTY_CHARACTERS

@pytest.fixture
def data_source():
    return factories.DataSourceFactory.create()


@pytest.mark.parametrize("attr, value, expected", [
    ("name", "TestName", "TestName"),
    ("name", " TestName", "TestName"),
    ("name", "TestName ", "TestName"),
    ("name", " Test Name ", "Test Name"),
    ("phone_number1", "1234 567 890", "1234 567 890"),
    ("phone_number1", " 1234 567 890", "1234 567 890"),
    ("phone_number1", "1234 567 890 ", "1234 567 890"),
    ("phone_number1", " 1234567890 ", "1234567890"),
    ("phone_number2", "1234 567 890", "1234 567 890"),
    ("phone_number2", " 1234 567 890", "1234 567 890"),
    ("phone_number2", "1234 567 890 ", "1234 567 890"),
    ("phone_number2", " 1234567890 ", "1234567890"),
    ("email1", "email@testmail.com", "email@testmail.com"),
    ("email1", " email@testmail.com", "email@testmail.com"),
    ("email1", "email@testmail.com ", "email@testmail.com"),
    ("email1", " email@ testmail.com ", "email@ testmail.com"),
    ("email2", "email@testmail.com", "email@testmail.com"),
    ("email2", " email@testmail.com", "email@testmail.com"),
    ("email2", "email@testmail.com ", "email@testmail.com"),
    ("email2", " email@ testmail.com ", "email@ testmail.com"),
    ("address", "5 Test Street", "5 Test Street"),
    ("address", " 5 Test Street", "5 Test Street"),
    ("address", "5 Test Street ", "5 Test Street"),
    ("address", " 5 Test Street ", "5 Test Street"),
    ("notes", "TestName", "TestName"),
    ("notes", " TestName\nHello\n\tThis is a new line.", "TestName\nHello\n\tThis is a new line."),
    ("notes", "TestName\nHello\n\tThis is a new line. ", "TestName\nHello\n\tThis is a new line."),
    ("notes", "TestName\nHello\n\tThis is a new line.", "TestName\nHello\n\tThis is a new line."),
    ("type", "person", "person"),
    ("type", "organisation", "organisation"),
])
def test_set_attribute(data_source: models.DataSource, attr: str, value, expected):
    common.test_set_attribute(data_source, attr, value, expected)


@pytest.mark.parametrize("attr, value", [
    ("email1", None),
    ("email1", ""),
    ("email1", "   "),
    ("updated_by_id", "this-is-not-a-uuid"),
    ("updated_by_id", 1)
])
def test_set_attribute_validation_error(data_source: models.DataSource, attr: str, value):
    common.test_set_attribute_validation_error(data_source, attr, value)

@pytest.mark.parametrize("attr, nullable", [
    ("updated_by_id", True)
])
def test_uuid(data_source: models.DataSource, attr: str, nullable: bool):
    common.validate_uuid(data_source, attr, str(uuid.uuid4()), nullable)


@pytest.mark.parametrize("form", [
    ({
        'name': "test name",
        'phone_number1': "test number",
        'phone_number2': "test number",
        'email1': "test email",
        'email2': "test email",
        'address': "test address",
        'notes': "test notes",
        'type': "person"
    }),
    ({
        'email1': "test email",
    }), ])
def test_insert_or_update(data_source: models.DataSource, form):
    data_source_old = copy.deepcopy(data_source)
    data_source._insert_or_update(form = form, new = False)
    assert data_source.email1 == form['email1']
    assert common.create_assertion(data_source.name, data_source_old.name, form['name'] if ('name' in form and form['name']) else None)
    assert common.create_assertion(data_source.phone_number1, data_source_old.phone_number1, form['phone_number1'] if ('phone_number1' in form and form['phone_number1']) else None)
    assert common.create_assertion(data_source.phone_number2, data_source_old.phone_number2, form['phone_number2'] if ('phone_number2' in form and form['phone_number2']) else None)
    assert common.create_assertion(data_source.email2, data_source_old.email2, form['email2'] if ('email2' in form and form['email2']) else None)
    assert common.create_assertion(data_source.address, data_source_old.address, form['address'] if ('address' in form and form['address']) else None)
    assert common.create_assertion(data_source.type, data_source_old.type, form['type'] if ('type' in form and form['type']) else None)


@pytest.mark.parametrize("form", [
    ({
        'name': "test name",
        'phone_number1': "test number",
        'phone_number2': "test number",
        'email2': "test email",
        'address': "test address",
        'notes': "test notes",
        'type': "person"
    }),
    ({
    }), ])
def test_insert_or_update_attribute_error(data_source: models.DataSource, form):
    with pytest.raises(AttributeError):
        data_source._insert_or_update(form = form, new = False)