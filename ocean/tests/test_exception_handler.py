import pytest

from ..app import exception_handler
from sqlalchemy import exc

TEST_STATEMENT = "SELECT * FROM table WHERE col=row;"

def factory_WarningException(message=None):
    return exception_handler.WarningException('' if not message else message)

def factory_CriticalException(message=None):
    return exception_handler.CriticalException('' if not message else message)

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

def test_warning_exception():
    assert exception_handler._parse_exception(factory_WarningException("Test warning")) == "Test warning"

def test_empty_warning_exception():
    assert exception_handler._parse_exception(factory_WarningException("")) == ""

def test_warning_exception_with_prefix():
    assert exception_handler._parse_exception(factory_WarningException("Test warning"), prefix="Warning") == "Warning: Test warning"

def test_critical_exception():
    critical_exc = factory_CriticalException("Test critical")
    with pytest.raises(exception_handler.CriticalException) as exc_info:
        exception_handler._parse_exception(factory_CriticalException("Test critical"))
    assert exc_info.value.args[0] == str(critical_exc)

def test_handle_exception_duplicate_error():
    value = "Apple"
    column = "name"
    assert exception_handler._parse_exception(factory_integrity_error(column=column, value=value)) == f"Unable to add record as it already exists ('{value}')."

def test_integrity_error_duplicate_with_prefix():
    value = "Apple"
    column = "name"
    assert exception_handler._parse_exception(factory_integrity_error(column=column, value=value), prefix="Warning") == f"Warning: Unable to add record as it already exists ('{value}')."

def factory_invalid_request_error(message):
    from sqlalchemy.exc import InvalidRequestError
    return InvalidRequestError(None, None, message)

def test_handle_exception_invalid_request_error():
    with pytest.raises(exception_handler.CriticalException) as exc_info:
        exception_handler._parse_exception(factory_invalid_request_error("Invalid request"))
        
def factory_programming_error(message):
    from sqlalchemy.exc import ProgrammingError
    return ProgrammingError(None, None, message)

def test_handle_exception_programming_error():
    with pytest.raises(exception_handler.CriticalException) as exc_info:
        exception_handler._parse_exception(factory_invalid_request_error("SQL syntax error"))

def test_data_error():
    from MySQLdb import DataError
    with pytest.raises(exception_handler.CriticalException) as exc_info:
        exception_handler._parse_exception(exc.DataError(orig=DataError("test"), statement=TEST_STATEMENT, params=None))
    assert exc_info.value.args[0] == "Database data error. This error has been logged."

def test_database_error():
    from MySQLdb import DatabaseError
    with pytest.raises(exception_handler.CriticalException) as exc_info:
        exception_handler._parse_exception(exc.DatabaseError(orig=DatabaseError("test"), statement=TEST_STATEMENT, params=None))
    assert exc_info.value.args[0] == "Database error. This error has been logged."

def test_invalid_request_error():
    with pytest.raises(exception_handler.CriticalException) as exc_info:
        exception_handler._parse_exception(exc.InvalidRequestError())
    assert exc_info.value.args[0] == "Database request is invalid. This error has been logged."

def test_dbapi_error():
    with pytest.raises(exception_handler.CriticalException) as exc_info:
        exception_handler._parse_exception(exc.DBAPIError(orig=None, statement=TEST_STATEMENT, params=None))
    assert exc_info.value.args[0] == "Database API error. This error has been logged."

def test_interface_error():
    from MySQLdb import InterfaceError
    with pytest.raises(exception_handler.CriticalException) as exc_info:
        exception_handler._parse_exception(exc.InterfaceError(orig=InterfaceError("test"), statement=TEST_STATEMENT, params=None))
    assert exc_info.value.args[0] == "Database connector error. This error has been logged."

def test_unbound_execution_error():
    with pytest.raises(exception_handler.CriticalException) as exc_info:
        exception_handler._parse_exception(exc.UnboundExecutionError())
    assert exc_info.value.args[0] == "Database operation attempted without a database connection. This error has been logged."

def test_no_reference_error():
    with pytest.raises(exception_handler.CriticalException) as exc_info:
        exception_handler._parse_exception(exc.NoReferenceError())
    assert exc_info.value.args[0] == "Database reference cannot be resolved. This error has been logged."

def test_multiple_results_found():
    assert exception_handler._parse_exception(exc.MultipleResultsFound()) == "A single database result was required but more than one were found."

def test_no_result_found():
    assert exception_handler._parse_exception(exc.NoResultFound()) == "A database result was required but none were found."

def test_resource_closed_error():
    with pytest.raises(exception_handler.CriticalException) as exc_info:
        exception_handler._parse_exception(exc.ResourceClosedError())
    assert exc_info.value.args[0] == "Database resource is closed. This error has been logged."

def test_pending_rollback_error():
    with pytest.raises(exception_handler.CriticalException) as exc_info:
        exception_handler._parse_exception(exc.PendingRollbackError())
    assert exc_info.value.args[0] == "Database rollback is pending. This error has been logged."
    
def test_invalid_request_error():
    with pytest.raises(exception_handler.CriticalException) as exc_info:
        exception_handler._parse_exception(exc.InvalidRequestError())
    assert exc_info.value.args[0] == "Database request is invalid. This error has been logged."
    
def test_timeout_error():
    with pytest.raises(exception_handler.CriticalException) as exc_info:
        exception_handler._parse_exception(exc.TimeoutError())
    assert exc_info.value.args[0] == "Database operation timed out. This error has been logged."

def test_disconnection_error():
    with pytest.raises(exception_handler.CriticalException) as exc_info:
        exception_handler._parse_exception(exc.DisconnectionError())
    assert exc_info.value.args[0] == "Database disconnection error. This error has been logged."

def test_other_errors():
    with pytest.raises(exception_handler.CriticalException) as exc_info:
        exception_handler._parse_exception(exc.SQLAlchemyError())
    assert exc_info.value.args[0] == "An unknown error ocurred with the database. Changes have been rolled back. This error has been logged."