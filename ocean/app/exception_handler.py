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

def parse_sqlalchemy_exc(exception: exc.SQLAlchemyError) -> str:
    """This method converts an SQLAlchemy Exception (base class sqlalchemy.exc.SQLAlchemyError)
    into a human-readable error message. SQLAlchemy errors all inherit from this base class.
    Currently this method is supported for the following error types. Any errors that are not
    these types are still converted to a string but not specially formatted:
    - `sqlalchemy.exc.IntegrityError` (constraints ignored)
    - `sqlalchemy.exc.OperationalError` (database disconnection)
    - `sqlalchemy.exc.ProgrammingError` (misformed query)
    
    Read more on SQLAlchemy exceptions here: `https://docs.sqlalchemy.org/en/20/core/exceptions.html#sqlalchemy.exc.SQLAlchemyError`

    Args:
        exception (sqlalchemy.exc.SQLAlchemyError): the exception to be parsed

    Returns:
        str: the parsed string
    """

    exc_msg = "" # Exception message (initially empty)
    if isinstance(exception, exc.IntegrityError):
        if "cannot be null" in exc_msg:
            column_name = exc_msg.split("Column '")[1].split("' cannot be null")[0]
            exc_msg += "Error: {} cannot be null. Please provide a valid value for {}.".format(column_name, column_name)
        elif exception.orig.args[0] == 1062:
            duplicate_value = exception.orig.args[1].split("Duplicate entry ")[1].split(" for key ")[0]
            exc_msg += f"Unable to add record as it already exists ({duplicate_value})."
        else:
            foreign_key_constraint = exc_msg.split('`')[3]
            exc_msg += "Cannot delete or update a parent row: this data row is relied upon by an entity in '{}'.".format(foreign_key_constraint)
    elif isinstance(exception, exc.OperationalError):
        exc_msg += "Operational exception occurred: {}.".format(exception.args[0])
    elif isinstance(exception, exc.ProgrammingError):
        exc_msg += "Programming exception occurred: {}.".format(exception.args[0])
    elif isinstance(exception, exc.InvalidRequestError):
        raise CriticalException(str(exception))
    else:
        raise CriticalException(str(exception))
    return exc_msg

def handle_exception(exception: exc.SQLAlchemyError | Exception, prefix="", session:orm.Session=None) -> str:
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

    error_string = prefix + ". " if prefix else ""
    
    if isinstance(exception, exc.SQLAlchemyError):
        error_string += parse_sqlalchemy_exc(exception)
        flash(error_string, category='error')
    elif isinstance(exception, WarningException):
        error_string += str(exception)
        flash(error_string, category='error')
    elif isinstance(exception, CriticalException):
        error_string += str(exception)
        logger.exception(error_string)
        raise CriticalException(error_string)
    elif isinstance(exception, Exception):
        error_string += str(exception)
        logger.exception(error_string)
        raise Exception(error_string)
    else:
        # This is theoretically never reached as Exception is a 
        # superclass of all possible exception types. However
        # if a non-exception type is passed to this function for
        # some reason this code will be reached.
        error_string += str(exception)
        logger.exception(error_string)
        raise Exception(str(exception))

    return error_string
