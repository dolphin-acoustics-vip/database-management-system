import datetime
from ..app import exception_handler
import pytest

# Values that signify an "empty string"
EMPTY_CHARACTERS = ["", " ", "\n", "\t"]
INVALID_CHARACTERS = ["/","\\","*","?","\"","<",">","|"," "]

DATE_FORMAT = ['%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M', '%Y-%m-%d', '%Y%m%d', '%Y%m%dT%H:%M:%S', '%Y%m%dT%H:%M']

def equate_timestamps(ts1, ts2):
    return ts1.year == ts2.year and ts1.month == ts2.month and ts1.day == ts2.day and ts1.hour == ts2.hour and ts1.minute == ts2.minute and ts1.second == ts2.second

def parse_timestamp(timestamp: datetime.datetime, format: str) -> tuple[str, datetime.datetime]:
    """Convert timestamp into a format, returning both the
    string-formatted timestamp and a new copy of the timestamp
    with only the information included in the formatted string.

    Args:
        timestamp (datetime.datetime): the timestamp to be formatted
        format (str): the format to use for the formatting
        
    Returns:
        tuple[str, datetime.datetime]: a tuple with the string-formatted timestamp and a new copy of the timestamp with only information included in the formatted string
    """
    time_string = timestamp.strftime(format)
    timestamp = datetime.datetime.strptime(time_string, format)
    return time_string, timestamp

def create_assertion(new, old, exp=None):
    """Create an assertion for the insert and update methods.
    
    `new` is the value of the attribute after calling the method.
    `old` is the value of the attribute before calling the method.
    `exp` is the expected value of the attribute (if `None` the assertion is `old == new`).
    """
    if exp != None and new != None:
        return new == exp
    elif exp == None and not new == None:
        return old == new
    else:
        return new == old

def test_set_attribute(model, attr, value, expected):
    setattr(model, attr, value)
    assert getattr(model, attr) == expected


def test_set_attribute_validation_error(model, attr, value):
    with pytest.raises(exception_handler.ValidationError):
        setattr(model, attr, value)

def validate_uuid(model, attr, uuid, nullable=False):
    import uuid
    
    test_uuid = uuid.uuid4()
    setattr(model, attr, test_uuid)
    assert getattr(model, attr) == test_uuid
    test_uuid = uuid.uuid4()
    setattr(model, attr, str(test_uuid))
    assert getattr(model, attr) == test_uuid
    
    with pytest.raises(exception_handler.ValidationError):
        setattr(model, attr, "this-is-not-a-uuid")
    with pytest.raises(exception_handler.ValidationError):
        setattr(model, attr, 1)
    if nullable:
        setattr(model, attr, None)
        assert getattr(model, attr) == None
    else:
        with pytest.raises(exception_handler.ValidationError):
            setattr(model, attr, None)
