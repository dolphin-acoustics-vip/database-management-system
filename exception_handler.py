from flask import flash
import sqlalchemy
from flask import session as client_session
from logger import logger
from sqlalchemy.exc import DBAPIError


# A number of custom exceptions have been defined which
# are raised for different reasons. See specific pydocs
# of each exception for more details.



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

        This exception is handled in handle_exception() by
        flashing the message on the screen.
        """
        super().__init__(message)


class NotFoundException(Exception):
    def __init__(self, message, details=""):
        super().__init__(message)
        self.details=details
        snapshot_date=client_session.get('snapshot_date')
    
    def get_details(self):
        return self.details



def parse_alchemy_error(error: sqlalchemy.exc.IntegrityError | sqlalchemy.exc.OperationalError | sqlalchemy.exc.ProgrammingError) -> str:
    """
    Extract important information from an sqlalchemy error. Currently the method
    supports the following error types:
    - IntegrityError (constraints ignored)
    - OperationalError (database disconnection)
    - ProgrammingError (misformed query)

    :param error: the SQLAlchemy error to be parsed
    :type error: sqlalchemy.exc.DBAPIError
    :return: a string with the parsed error message
    """

    if isinstance(error, sqlalchemy.exc.IntegrityError):
        error_message = str(error)
        if "cannot be null" in error_message:
            column_name = error_message.split("Column '")[1].split("' cannot be null")[0]
            return "Error: {} cannot be null. Please provide a valid value for {}.".format(column_name, column_name)
        elif error.orig.args[0] == 1062 and "Duplicate entry" in error_message:
            duplicate_value = error_message.split("Duplicate entry ")[1].split(" for key")[0]
            duplicate_attribute = error_message.split("for key '")[1].split("'")[0]
            return "Duplicate entry: {} for {}.".format(duplicate_value, duplicate_attribute)
        else:
            foreign_key_constraint = error_message.split('`')[3]
            return "Cannot delete or update a parent row: this data row is relied upon by an entity in '{}'.".format(foreign_key_constraint)
    elif isinstance(error, sqlalchemy.exc.OperationalError):
        return "Operational error occurred: {}.".format(error.args[0])
    elif isinstance(error, sqlalchemy.exc.ProgrammingError):
        return "Programming error occurred: {}.".format(error.args[0])
    else:
        return "An error occurred: {}.".format(str(error))    




def handle_exception(session, exception, prefix="") -> str:
    """
    Handle exception and rollback the session. Where possible the
    exception is dissected and a human-readable message is passed
    to the Flask flash() method. For an unknown or severe error,
    a new Exception is raised to then be caught by app.py.

    :param session: SQLAlchemy session
    :param exception: Exception or SQLAlchemy DBAPIError to be processed
    :type exception: sqlalchemy.exc.DBAPIError | Exception
    :param prefix: Prefix to be added before the error message (default empty)
    :type prefix: str

    :return: error_string: Parsed error message
    """
    return handle_sqlalchemy_exception(session, exception, prefix=prefix)

def handle_sqlalchemy_exception(session, sqlAlchemy_exception, prefix="") -> None:
    from models import File
    from sqlalchemy.exc import IntegrityError

    # Access the newly added File objects
    new_file_objects = [obj for obj in session.new if isinstance(obj, File)]
    
    # Access the modified File objects
    dirty_file_objects = [obj for obj in session.dirty if isinstance(obj, File)]

    #new_file_objects.extend(dirty_file_objects)

    for file_object in new_file_objects:
        file_object.rollback(session)

    session.rollback()

    error_string = prefix + ". " if prefix else ""
    
    if isinstance(sqlAlchemy_exception, IntegrityError):
        error_string += parse_alchemy_error(sqlAlchemy_exception)
        flash(error_string, category='error')
    elif isinstance(sqlAlchemy_exception, WarningException):
        error_string += str(sqlAlchemy_exception)
        flash(error_string, category='error')
    elif isinstance(sqlAlchemy_exception, CriticalException):
        error_string += str(sqlAlchemy_exception)
        raise CriticalException(error_string)
    elif isinstance(sqlAlchemy_exception, Exception):
        error_string += str(sqlAlchemy_exception)
        logger.exception(error_string)
        raise sqlAlchemy_exception
    else:
        error_string += str(sqlAlchemy_exception)
        flash(error_string, category='error')
        logger.exception(error_string)

    return error_string
