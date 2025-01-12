# Copyright (c) 2024
#
# This file is part of OCEAN.
#
# OCEAN is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# OCEAN is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with OCEAN.  If not, see <https://www.gnu.org/licenses/>.

# Third-party imports
from flask import flash, session as client_session
from sqlalchemy import exc
from sqlalchemy import orm

# Local application imports
from .logger import logger
from .response_handler import JSONResponse

class CriticalException(Exception):
    def __init__(self, message:str):
        """
        Raise any exception that is an 'unfixable' error. 
        For example if an argument in a request has become
        corrupted and so a database query returns None. 

        This exception is handled in app.py by redirecting
        the user to a custom error page.
        """
        super().__init__(message)

class WarningException(Exception):
    def __init__(self, message:str):
        """
        Raise any exception that is due to a user fault.
        For example an incorrect data entry that is caught
        before a database query.

        Wherever it is possible for this exception to be raised,
        it should be caught by exception_handler.handle_exception().
        """
        super().__init__(message)


class ValidationError(WarningException):
    """An error that is to be raised when a validation test for data
    fails. This is typically caused by a bad request from a user.
    """

    def __init__(self, field:str, required:str, value):
        super().__init__(f"Field '{str(field)}' is not of type {str(required)} (given '{str(value)}').")

def _parse_sqlalchemy_exc(exception: exc.SQLAlchemyError) -> str:
    """Process an SQLAlchemy exception (a subclass of `sqlalchemy.exc.SQLAlchemyError`).
    In most cases SQLAlchemy exceptions are thrown because of unexpected issues with the
    structure of the database or connection issues.

    Args:
        exception (exc.SQLAlchemyError): the subclass of SQLAlchemyError to be parsed.

    Raises:
        CriticalException: if the SQLAlchemy error is one that indicates a problem with the 
        schema/connection/code (which needs to be fixed).

    Returns:
        str: a human-readable error message (if the CriticalException is not raised). This indicates that 
        the exception can be handled by a session rollback and the string should be shown to the user to
        inform them what happened.
    """
    exc_msg = "" # Exception message (initially empty)
    if isinstance(exception, exc.NotSupportedError):
        # Wraps a DB-API NotSupportedError.
        logger.exception(exception)
        raise CriticalException(str("Database operation is not supported. This error has been logged."))
    if isinstance(exception, exc.ProgrammingError):
        # Wraps a DB-API ProgrammingError.
        logger.exception(exception)
        raise CriticalException(str("Database operation is malformed. This error has been logged."))
    if isinstance(exception, exc.InternalError):
        # Wraps a DB-API InternalError.
        logger.exception(exception)
        raise CriticalException(str("Internal database error ocurred. This error has been logged."))
    if isinstance(exception, exc.IntegrityError):
        # Wraps a DB-API IntegrityError.
        # IntegrityError is the most common type of error and refers to some operation that violates contraints
        if "cannot be null" in exc_msg:
            column_name = exc_msg.split("Column '")[1].split("' cannot be null")[0]
            exc_msg += "Error: {} cannot be null. Please provide a valid value for {}.".format(column_name, column_name)
        elif exception.orig.args[0] == 1062:
            duplicate_value = exception.orig.args[1].split("Duplicate entry ")[1].split(" for key ")[0]
            exc_msg += f"Unable to add record as it already exists ({duplicate_value})."
        else:
            logger.exception(exception)
            exc_msg += "Database integrity error. This error has been logged."
    elif isinstance(exception, exc.OperationalError):
        # Wraps a DB-API OperationalError.
        logger.exception(exception)
        raise CriticalException("Database is not operational. This error has been logged.")
    elif isinstance(exception, exc.DataError):
        # Wraps a DB-API DataError.
        logger.exception(exception)
        raise CriticalException("Database data error. This error has been logged.")
    elif isinstance(exception, exc.DatabaseError):
        # Wraps a DB-API DatabaseError.
        logger.exception(exception)
        raise CriticalException("Database error. This error has been logged.")
    elif isinstance(exception, exc.InterfaceError):
        logger.exception(exception)
        raise CriticalException("Database connector error. This error has been logged.")
    elif isinstance(exception, exc.UnboundExecutionError):
        # SQL was attempted without a database connection to execute it on.
        logger.exception(exception)
        raise CriticalException("Database operation attempted without a database connection. This error has been logged.")
    elif isinstance(exception, exc.NoReferenceError):
        # Raised by ``ForeignKey`` to indicate a reference cannot be resolved.
        # Has two subclasses: 
        # - NoReferencedTableError: Raised by ``ForeignKey`` when the referred ``Table`` cannot be located.
        # - NoReferencedColumnError: Raised by ``ForeignKey`` when the referred ``Column`` cannot be located.
        logger.exception(exception)
        raise CriticalException("Database reference cannot be resolved. This error has been logged.")
    elif isinstance(exception, exc.MultipleResultsFound):
        # A single database result was required but more than one were found.
        return "A single database result was required but more than one were found."
    elif isinstance(exception, exc.NoResultFound):
        # A database result was required but none was found.
        return "A database result was required but none were found."
    elif isinstance(exception, exc.ResourceClosedError):
        # An operation was requested from a connection, cursor, or other object that's in a closed state.
        logger.exception(exception)
        raise CriticalException("Database resource is closed. This error has been logged.")
    elif isinstance(exception, exc.PendingRollbackError):
        # A transaction has failed and needs to be rolled back before continuing.
        logger.exception(exception)
        raise CriticalException("Database rollback is pending. This error has been logged.")
    elif isinstance(exception, exc.InvalidRequestError):
        # SQLAlchemy was asked to do something it can't do.
        logger.exception(exception)
        raise CriticalException("Database request is invalid. This error has been logged.")
    elif isinstance(exception, exc.DBAPIError):
        # Raised when the execution of a database operation fails.
        # Note that the exception may be wrapped by a more specific exception.
        # These exceptions are already managed above.
        logger.exception(exception)
        raise CriticalException("Database API error. This error has been logged.")
    elif isinstance(exception, exc.TimeoutError):
        # Raised when a connection pool times out on getting a connection.
        logger.exception(exception)
        raise CriticalException("Database operation timed out. This error has been logged.")
    elif isinstance(exception, exc.DisconnectionError):
        # A disconnect is detected on a raw DB-API connection.
        logger.exception(exception)
        raise CriticalException("Database disconnection error. This error has been logged.")
    else:
        # All other subclasses of SQLAlchemyException not handled above
        logger.exception(exception)
        raise CriticalException("An unknown error ocurred with the database. Changes have been rolled back. This error has been logged.")
    
    return exc_msg

def _parse_exception(exception: exc.SQLAlchemyError | Exception, prefix: str | None = None) -> str:
    """Given an exception this method parses it into a human-readable string. If the exception
    if of unknown type `Exception` or type `CriticalException` or an un-fixable type of 
    `sqlalchemy.exc.SQLAlchemyError` then the exception is raised and logged. If not then
    the exception is parsed and returned as a string.

    Args:
        exception (exc.SQLAlchemyError | Exception): the exception to be parsed.
        prefix (str): an optional prefix to be added to the parsed exception. Defaults to `None`. Do not provide punctuation at the end of the prefix as it is automatically added.

    Raises:
        CriticalException: if `exception` is `CriticalException`
        Exception: if `exception` is `sqlalchemy.exc.SQLAlchemyError` but cannot be addressed with a session rollback
        Exception: if `exception` is `Exception` but not `WarningException`

    Returns:
        str: _description_
    """
    return_string = (prefix + ": ") if prefix else ""
    if isinstance(exception, exc.SQLAlchemyError):
        return return_string + _parse_sqlalchemy_exc(exception)
    elif isinstance(exception, ValidationError):
        return return_string + str(exception)
    elif isinstance(exception, WarningException):
        return return_string + str(exception)
    elif isinstance(exception, CriticalException):
        logger.exception(str(exception))
        raise CriticalException(str(exception))
    else:
        logger.exception(str(exception))
        raise CriticalException("An unexpected error ocurred. It has been logged. Please notify your administrator and try again later.")

def handle_exception(exception: exc.SQLAlchemyError | Exception, prefix: str | None = None, session:orm.Session=None, show_flash:bool=True) -> str:
    """Parse an exception and rollback a SQLAlchemy session. The way in which an exception is parsed
    is dependent on the type of exception. There are three categories:

    - `sqlalchemy.exc.SQLAlchemyError`: The session is rolled back and the SQLAlcemy exception is parsed and then passed to flask.flash().
    - `exception_handler.WarningException`: The session is rolled back and the exception message is passed straight to flask.flash()
    - `exception_handler.CriticalException` and `Exception`: The session is rolled back and the exception is raised again (to be caught at some higher level). Information is also sent to the logger.
    
    Note: `SQLAlchemyError` is the superclass of all SQLAlchemy exceptions. `WarningException` and `CriticalException` are both subclasses of `Exception`.
    
    The logic behind these three exceptions is as follows. Database exceptions (`SQLAlchemyError`) are handled by the session rollback (so the only requirement is to parse
    and notify the user). Warning exceptions (`WarningException`) are raised only when non-critical issues occur (such as incorrect input from the user). Critical
    exceptions (`CriticalException` and `Exception`) are raised when something unexpected or unfixable occurs and information needs to be logged.
    
    A `prefix` can be provided which is then added before the parsed error message. If no `session` is provided then no session will be rolled back.

    Args:
        exception (sqlalchemy.exc.SQLAlchemyError | Exception): The exception to be handled
        prefix (str, optional): A prefix to be added before the error message. Defaults to "".
        session (_type_, optional): A session to be rolled back. Defaults to None.

    Raises:
        CriticalException: When `exception` is `CriticalException`
        Exception: When `exception` is `Exception`

    Returns:
        str: The parsed error message (note that when `CriticalException` or `Exception` are re-raised nothing will be returned)
    """

    

    if session:
        # Rollback any newly created File objects
        from .models import File
        for file_object in [obj for obj in session.new if isinstance(obj, File)]:
            if hasattr(file_object, 'rollback'): file_object.rollback(session)
        # Rollback the ORM session
        session.rollback()

    error_string = _parse_exception(exception=exception, prefix = prefix)
    if show_flash: flash(error_string, category='error')
    return error_string