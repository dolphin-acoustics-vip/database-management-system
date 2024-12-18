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

def test_hasattr_updated_by(data_source):
    assert hasattr(data_source, "updated_by_id")
    assert hasattr(data_source, "updated_by")
    assert hasattr(data_source, "set_updated_by_id")
        
def test_set_updated_by_id(data_source: models.RecordingPlatform):
    user_id = uuid.uuid4()
    data_source.set_updated_by_id(user_id)
    assert data_source.updated_by_id == user_id

@pytest.mark.parametrize("c", EMPTY_CHARACTERS)
def test_set_updated_by_id_empty(data_source: models.RecordingPlatform, c: str):
    with pytest.raises(exception_handler.WarningException):
        data_source.set_updated_by_id(c)

def test_set_updated_by_id_wrong_type(data_source: models.RecordingPlatform):
    with pytest.raises(exception_handler.WarningException):
        data_source.set_updated_by_id("this-is-not-a-uuid")

def test_hasattr_getters(data_source: models.DataSource):
    assert hasattr(data_source, "get_name")
    assert hasattr(data_source, "get_phone_number1")
    assert hasattr(data_source, "get_phone_number2")
    assert hasattr(data_source, "get_email1")
    assert hasattr(data_source, "get_email2")
    assert hasattr(data_source, "get_address")
    assert hasattr(data_source, "get_notes")
    assert hasattr(data_source, "get_type")
    
def test_hasattr_setters(data_source: models.DataSource):
    assert hasattr(data_source, "set_name")
    assert hasattr(data_source, "set_phone_number1")
    assert hasattr(data_source, "set_phone_number2")
    assert hasattr(data_source, "set_email1")
    assert hasattr(data_source, "set_email2")
    assert hasattr(data_source, "set_address")
    assert hasattr(data_source, "set_notes")
    assert hasattr(data_source, "set_type")

def test_get_name(data_source: models.DataSource):
    data_source.name = "Test Name"
    assert data_source.get_name() == "Test Name"
    
def test_set_name(data_source: models.DataSource):
    VALUE = "Test Name"
    data_source.set_name(VALUE)
    assert data_source.name == VALUE
    data_source.set_name("  " + VALUE + "\n ")
    assert data_source.name == VALUE

@pytest.mark.parametrize("c", EMPTY_CHARACTERS)
def test_set_name_none(data_source: models.DataSource, c: str):
    data_source.set_name(c)
    assert data_source.name == "" if c is not None else data_source.name == None
    

def test_get_phone_number1(data_source: models.DataSource):
    data_source.phone_number1 = "1234 567 890"
    assert data_source.get_phone_number1() == "1234 567 890"

def test_set_phone_number1(data_source: models.DataSource):
    VALUE = "1234 567 890"
    data_source.set_phone_number1(VALUE)
    assert data_source.phone_number1 == VALUE
    data_source.set_phone_number1("  " + VALUE + "\n ")
    assert data_source.phone_number1 == VALUE

@pytest.mark.parametrize("c", EMPTY_CHARACTERS)
def test_set_phone_number1_none(data_source: models.DataSource, c: str):
    data_source.set_phone_number1(c)
    assert data_source.phone_number1 == "" if c is not None else data_source.name == None
    

def test_get_phone_number2(data_source: models.DataSource):
    data_source.phone_number2 = "1234 567 890"
    assert data_source.get_phone_number2() == "1234 567 890"
    
def test_set_phone_number2(data_source: models.DataSource):
    VALUE = "1234 567 890"
    data_source.set_phone_number2(VALUE)
    assert data_source.phone_number2 == VALUE
    data_source.set_phone_number2("  " + VALUE + "\n ")
    assert data_source.phone_number2 == VALUE

@pytest.mark.parametrize("c", EMPTY_CHARACTERS)
def test_set_phone_number2_none(data_source: models.DataSource, c: str):
    data_source.set_phone_number2(c)
    assert data_source.phone_number2 == "" if c is not None else data_source.name == None
    
    
def test_get_email1(data_source: models.DataSource):
    data_source.email1 = "email@testmail.com"
    assert data_source.get_email1() == "email@testmail.com"

def test_set_email1(data_source: models.DataSource):
    VALUE = "email@testmail.com"
    data_source.set_email1(VALUE)
    assert data_source.email1 == VALUE
    data_source.set_email1("  " + VALUE + "\n ")
    assert data_source.email1 == VALUE

@pytest.mark.parametrize("c", EMPTY_CHARACTERS)
def test_set_email1_none(data_source: models.DataSource, c: str):
    data_source.set_email1(c)
    assert data_source.email1 == "" if c is not None else data_source.name == None
    

def test_get_email2(data_source: models.DataSource):
    data_source.email2 = "email@testmail.com"
    assert data_source.get_email2() == "email@testmail.com"

def test_set_email2(data_source: models.DataSource):
    VALUE = "email@testmail.com"
    data_source.set_email2(VALUE)
    assert data_source.email2 == VALUE
    data_source.set_email2("  " + VALUE + "\n ")
    assert data_source.email2 == VALUE

@pytest.mark.parametrize("c", EMPTY_CHARACTERS)
def test_set_email2_none(data_source: models.DataSource, c: str):
    data_source.set_email2(c)
    assert data_source.email2 == "" if c is not None else data_source.name == None
    

def test_get_address(data_source: models.DataSource):
    data_source.address = "15 Test Street, KY16"
    assert data_source.get_address() == "15 Test Street, KY16"
    
def test_set_address(data_source: models.DataSource):
    VALUE = "15 Test Street, KY16"
    data_source.set_address(VALUE)
    assert data_source.address == VALUE
    data_source.set_address("  " + VALUE + "\n ")
    assert data_source.address == VALUE

@pytest.mark.parametrize("c", EMPTY_CHARACTERS)
def test_set_address_none(data_source: models.DataSource, c: str):
    data_source.set_address(c)
    assert data_source.address == "" if c is not None else data_source.name == None
    
    
def test_get_notes(data_source: models.DataSource):
    data_source.notes = "Note 1\nNote 2"
    assert data_source.get_notes() == "Note 1\nNote 2"

def test_set_notes(data_source: models.DataSource):
    VALUE = "Note 1\nNote 2"
    data_source.set_notes(VALUE)
    assert data_source.notes == VALUE
    data_source.set_notes("  " + VALUE + "\n ")
    assert data_source.notes == VALUE

@pytest.mark.parametrize("c", EMPTY_CHARACTERS)
def test_set_notes_none(data_source: models.DataSource, c: str):
    data_source.set_notes(c)
    assert data_source.notes == "" if c is not None else data_source.name == None
    

def test_get_type(data_source: models.DataSource):
    data_source.type = "person"
    assert data_source.get_type() == "person"
    data_source.type = "organisation"
    assert data_source.get_type() == "organisation"

def test_set_type(data_source: models.DataSource):
    data_source.set_type("person")
    assert data_source.type == "person"
    data_source.set_type("organisation")
    assert data_source.type == "organisation"
    
@pytest.mark.parametrize("c", EMPTY_CHARACTERS)
def test_set_notes_none(data_source: models.DataSource, c: str):
    data_source.set_type(c)
    assert data_source.type == None

def test_set_type_wrong(data_source: models.DataSource):
    with pytest.raises(exception_handler.WarningException):
        data_source.set_type("not-an-available-option")
