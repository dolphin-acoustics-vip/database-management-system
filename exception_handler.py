from flask import flash
import sqlalchemy
from flask import session as client_session

def parse_alchemy_error(error):
    if isinstance(error, sqlalchemy.exc.IntegrityError):
        error_message = str(error)
        if "cannot be null" in error_message:
            column_name = error_message.split("Column '")[1].split("' cannot be null")[0]
            return "Error: {} cannot be null. Please provide a valid value for {}.".format(column_name, column_name)
        elif error.orig.args[0] == 1062 and "Duplicate entry" in error_message:
            duplicate_value = error_message.split("Duplicate entry ")[1].split(" for key")[0]
            duplicate_attribute = error_message.split("for key '")[1].split("'")[0]
            return "Duplicate entry"
        else:
            foreign_key_constraint = error_message.split('`')[3]
            return "Cannot delete or update a parent row: this data row is relied upon by an entity in '{}'.".format(foreign_key_constraint)
    elif isinstance(error, sqlalchemy.exc.OperationalError):
        return "Operational error occurred: {}.".format(error.args[0])
    elif isinstance(error, sqlalchemy.exc.ProgrammingError):
        return "Programming error occurred: {}.".format(error.args[0])
    else:
        return "An error occurred: {}.".format(str(error))    


def handle_exception(exception: Exception | str, session=None) -> None:
    """
    Handle exception and rollback the session.
    
    Parameters:
    - exception: Exception or string
    - session: SQLAlchemy session
    
    Returns:
    - string: Parsed error message
    """
    
    flash(str(exception), 'error')
    if session:
        session.rollback()
    return str(exception)

def handle_sqlalchemy_exception(session, sqlAlchemy_exception: sqlalchemy.exc.SQLAlchemyError) -> None:
    """
    Parse SQLAlchemy errors and return a human-readable message which can be displayed in the UI
    where necessary. This method can parse database errors such as illegal duplicates, null values,
    foreign key constraints, operational errors, and programming errors. Where an error is
    unrecognised, the default sqlalchemy error message is returned with a prefix.
    
    This method will also roll back the changes in the session.
    """
    from models import File

    if isinstance(sqlAlchemy_exception, sqlalchemy.exc.IntegrityError):
        error_string = parse_alchemy_error(sqlAlchemy_exception)
    else:
        error_string = str(sqlAlchemy_exception)

    # Access the newly added File objects
    new_file_objects = [obj for obj in session.new if isinstance(obj, File)]
    
    # Access the modified File objects
    dirty_file_objects = [obj for obj in session.dirty if isinstance(obj, File)]

    #new_file_objects.extend(dirty_file_objects)

    print("DIRTY FILE OBJECTS", dirty_file_objects)
    print("NEW FILE OBJECTS", new_file_objects)
    for file_object in new_file_objects:
        file_object.rollback(session)

    flash(error_string, 'error')
    session.rollback()
    return error_string

class NotFoundException(Exception):
    def __init__(self, message):
        super().__init__(message)
        snapshot_date=client_session.get('snapshot_date')