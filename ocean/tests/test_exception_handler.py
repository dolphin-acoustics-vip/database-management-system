import pytest

from ..app import exception_handler
from sqlalchemy import exc

def factory_WarningException(message=None):
    return exception_handler.WarningException('Test warning' if not message else message)

def factory_CriticalException(message=None):
    return exception_handler.CriticalException('Test critical' if not message else message)

def factory_Exception(message=None):
    return Exception('Test exception' if not message else message)

def factory_SQLAlchemyError(message=None):
    return exc.SQLAlchemyError('Test sqlalchemy error' if not message else message)

def factory_integrity_error(column, value):
    """
    Creates a mock IntegrityError instance for testing purposes.

    Args:
        message (str): The query that caused the error.
        column (str): The name of the column that caused the error.
        value (str): The value that caused the duplicate entry error.

    Returns:
        sqlalchemy.exc.IntegrityError: A mock IntegrityError instance.
    """
    from MySQLdb import IntegrityError
    params = ('val1','val2','val3')
    statement = "INSERT INTO table (column) VALUES (value)"   
    integrity_error = IntegrityError(1062, str(f"Duplicate entry '{value}' for key '{column}'"))
    return exc.IntegrityError(statement=statement, orig=integrity_error, params=params)

def test_handle_exception_duplicate_error():
    value = "Apple"
    column = "name"
    assert exception_handler.parse_sqlalchemy_exc(factory_integrity_error(column=column, value=value)) == f"Unable to add record as it already exists ('{value}')."

def factory_invalid_request_error(message):
    from sqlalchemy.exc import InvalidRequestError
    return InvalidRequestError(None, None, message)

def test_handle_exception_invalid_request_error():
    with pytest.raises(exception_handler.CriticalException) as exc_info:
        exception_handler.parse_sqlalchemy_exc(factory_invalid_request_error("Invalid request"))
        
def factory_programming_error(message):
    from sqlalchemy.exc import ProgrammingError
    return ProgrammingError(None, None, message)

def test_handle_exception_programming_error():
    with pytest.raises(exception_handler.CriticalException) as exc_info:
        exception_handler.parse_sqlalchemy_exc(factory_invalid_request_error("SQL syntax error"))
        
# FILL THIS UP WITH THE REST OF THE POSSIBLE SQLALCHEMY ERRORS!!!