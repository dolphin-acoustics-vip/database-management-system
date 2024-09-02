# db_handler.py
from datetime import datetime
from functools import wraps
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from flask_sqlalchemy import SQLAlchemy
import sqlalchemy
from flask_login import LoginManager, current_user
from flask import abort, g, render_template, request, session as client_session
import os
import exception_handler
from logger import logger


###
# INITIALISING FILE SPACE
###

DATA_DIR = 'data'
TEMP_DIR = 'tempdir'
TRASH_DIR = 'trash'

# Define the file space folder and get the Google API key from a file
FILE_SPACE_FILENAME = 'file_space_path.txt'
FILE_SPACE_PATH = ''
if os.path.exists(FILE_SPACE_FILENAME):
    with open(FILE_SPACE_FILENAME, 'r') as f:
        FILE_SPACE_PATH = f.read()
        if FILE_SPACE_PATH == None or FILE_SPACE_PATH.strip() == '':
            logger.critical(f"File space path found in '{FILE_SPACE_FILENAME}' however the file is empty. Cannot proceed.")
            startup_error_flag = True
        elif not os.path.exists(FILE_SPACE_PATH):
            logger.critical(f"File space path found in '{FILE_SPACE_FILENAME}' however the path '{FILE_SPACE_PATH}' does not exist. Cannot proceed.")
            startup_error_flag = True
        else:
            logger.info(f"Assigned file space '{FILE_SPACE_PATH}'")
else:
    logger.critical(f"File space path configuration file not found in '{FILE_SPACE_FILENAME}'")
    startup_error_flag = True

def get_trash_path():
    if not os.path.exists(os.path.join(FILE_SPACE_PATH, TRASH_DIR)):
        os.makedirs(os.path.join(FILE_SPACE_PATH, TRASH_DIR))
    return os.path.join(FILE_SPACE_PATH, TRASH_DIR)

def get_file_space_path():
    if not os.path.exists(os.path.join(FILE_SPACE_PATH, DATA_DIR)):
        os.makedirs(os.path.join(FILE_SPACE_PATH, DATA_DIR))
    return os.path.join(FILE_SPACE_PATH, DATA_DIR)

def get_tempdir():
    if not os.path.exists(os.path.join(FILE_SPACE_PATH, TEMP_DIR)):
        os.makedirs(os.path.join(FILE_SPACE_PATH, TEMP_DIR))
    return os.path.join(FILE_SPACE_PATH, TEMP_DIR)


###
# INITIALISE DATABASE
###

db = SQLAlchemy()

def init_db(app, create_database=None):
    """
    Initialise the database using the given Flask app.
    
    The function can also create the database if a file path to a SQL script is provided in the
    create_database parameter. The SQL script should contain the schema for the database.
    
    The function also sets up the Flask-Login extension. The load_user function is used by
    Flask-Login to find a user by their id. The function takes a user_id as an argument and
    returns the user object if found, otherwise None.
    
    :param app: the Flask app
    :type app: Flask
    :param (optional) create_database: the path to a SQL script to create the database
    :type create_database: str
    :return: the database object
    :rtype: SQLAlchemy
    """

    db.init_app(app)
    
    if create_database:
        with app.app_context():
            with db.engine.connect() as conn:
                with app.open_resource(create_database, mode='r') as f:
                    sql_script = f.read()
                    conn.execute(db.text(sql_script))
    
            @sqlalchemy.event.listens_for(Session, 'before_commit')
            def before_commit(session: sessionmaker):
                """
                Catch the session.commit command from all areas of the program to add logged in user data to the row(s)
                being committed in the database. This method will go through all UPDATE and INSERT commands in a 
                session and will only add user data to the tables that have a column for it.
                """
                # session.dirty gives all modified (UPDATE) rows and session.new gives all new (INSERT) rows
                for obj in session.dirty.union(session.new):
                    if obj.__class__.__name__ == 'Recording' or obj.__class__.__name__ == 'Encounter' or obj.__class__.__name__ == 'File' or obj.__class__.__name__ == 'RecordingPlatform' or obj.__class__.__name__ == 'DataSource' or obj.__class__.__name__ == 'Selection' or obj.__class__.__name__ == 'Species':
                        obj.updated_by_id = current_user.id


    # Setup user login
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)
    @login_manager.user_loader
    def load_user(user_id: str):
        """
        User loader function for Flask-Login extension. This function is used to find a
        user by their id. The function takes a user_id as an argument and returns the user
        object if found, otherwise None.
        """
        from sqlalchemy.exc import OperationalError
        try:
            from models import User
            # Since the user_id is just the primary key of the user table, use it in the query for the user
            return User.query.get(user_id)
        except OperationalError:
            return None



    return db

def get_engine():
    return db.engine

def get_session():
    engine = get_engine()
    Session = sessionmaker(bind=engine, autoflush=False)
    return Session()

Session = get_session


def get_snapshot_date_from_session():
    """
    Gets the snapshot date from the session.
    """
    return client_session.get('snapshot_date')

def save_snapshot_date_to_session(snapshot_date):
    """
    Saves the snapshot date to the session.
    """
    client_session['snapshot_date'] = snapshot_date

def clean_directory(root_directory):
    """
    Walk through a given directory and remove any empty directories.

    :param root_directory: The root directory to start cleaning
    :type root_directory: str
    """
    # Get the root directory of the project
    for root, dirs, files in os.walk(root_directory, topdown=False):
        for dir in dirs:
            dir_path = os.path.join(root, dir)
            # If there exist no sub directories, remove it
            if not os.listdir(dir_path):
                os.rmdir(dir_path)


# A number of annotations that can be applied to flask route methods to restrict access to certain
# user access level permissions.

def exclude_role_1(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if current_user.is_authenticated and current_user.role_id != 1:
            return func(*args, **kwargs)
        else:
            abort(403)
    return wrapper
                   
def exclude_role_2(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if current_user.is_authenticated and current_user.role_id != 2:
            return func(*args, **kwargs)
        else:
            abort(403)
    return wrapper

def exclude_role_3(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if current_user.is_authenticated and current_user.role_id != 3:
            return func(*args, **kwargs)
        else:
            abort(403)
    return wrapper

def exclude_role_4(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if current_user.is_authenticated and current_user.role_id != 4:
            return func(*args, **kwargs)
        else:
            abort(403)
    return wrapper 

def require_live_session(func):
    """
    An annotation to restrict access to a particular route whenever the user views the program in an 
    archive mode. This method should be used on all methods which complete INSERT or UPDATE operations
    on the database, as these must only ever be done in live view.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # If snapshot_date exists in session cookies then the program is in archive mode
        snapshot_date = client_session.get('snapshot_date')
        if not snapshot_date:
            return func(*args, **kwargs)
        else:
            # Redirect to a page indicating unauthorized access
            referrer_url = request.headers.get('Referer')
            return render_template("require-live-session.html", user=current_user, original_url=request.url, referrer_url=referrer_url)
    return wrapper



def get_system_time_request_recording(session:sessionmaker, user_id:str=None, assigned_user_id:str=None, created_date_filter:str=None, species_filter_str:str=None, override_snapshot_date:str=None):
    """
    Retrieves all recording records for the given filters. The recording table is joined with a number of other tables including encounter, species, and user to
    provide additional information. See method in detail to learn more about variable names assigned to columns of the other tables in the join.

    If a created_date_filter is passed, the query will be filtered only by selections which lie between the date they were created and today (or the snapshot
    date if currently in the user session).

    :param session: the sqlalchemy session object
    :param user_id: the id of the user to filter by if specified
    :param assigned_user_id: the id of the assigned user to filter by if specified
    :param created_date_filter: the date after which the recordings are to be filtered if specified
    :param species_filter_str: a comma separated string of species ids to filter by if specified
    :param override_snapshot_date: if specified, use this instead of the snapshot_date from the session cookies
    :return: a list of dictionaries with column names as keys
    :rtype: list
    """
    from models import Recording
    snapshot_date=client_session.get('snapshot_date') if override_snapshot_date is None else override_snapshot_date

    columns = "rec.id, rec.created_datetime, rec.start_time, rec.status, enc.id enc_id, enc.encounter_name enc_encounter_name, enc.location enc_location, sp.id sp_id, sp.species_name sp_species_name, assignment.created_datetime assignment_created_datetime, assignment.completed_flag assignment_completed_flag, COUNT(CASE WHEN sel.traced = 1 AND sel.deactivated = 0 THEN sel.id END) traced_count, COUNT(CASE WHEN sel.deactivated = 1 THEN sel.id END) deactivated_count, COUNT(CASE WHEN sel.traced IS NULL AND sel.deactivated = 0 THEN sel.id END) untraced_count, assignment_user.id assignment_user_id, assignment_user.name assignment_user_name, assignment_user.login_id assignment_user_login_id"
    joins = "LEFT JOIN encounter AS enc ON rec.encounter_id = enc.id LEFT JOIN species AS sp ON enc.species_id = sp.id LEFT JOIN assignment ON rec.id = assignment.recording_id LEFT JOIN user AS assignment_user ON assignment.user_id = assignment_user.id LEFT JOIN selection AS sel ON rec.id = sel.recording_id"

    if snapshot_date: query_str="SELECT {} FROM {} FOR SYSTEM_TIME AS OF '{}' AS sel".format(columns, Recording.__tablename__, snapshot_date)
    else: query_str="SELECT {} FROM {} AS rec".format(columns, Recording.__tablename__)
    query_str += " {}".format(joins)
    next_clause = "WHERE"
    if assigned_user_id:
        query_str += " {} assignment.user_id = '{}'".format(next_clause, assigned_user_id)
        next_clause = "AND"
    if created_date_filter:
        query_str += " {} rec.created_datetime >= '{}'".format(next_clause, created_date_filter)
        next_clause = "AND"
    if species_filter_str is not None and species_filter_str != '':
        species_filter = species_filter_str.split(",")
        species_filter_str = ", ".join("'" + item + "'" for item in species_filter)
        query_str += " {} sp.id IN ({})".format(next_clause, species_filter_str)

    query_str += " GROUP BY rec.id, rec.start_time, enc.id, enc.encounter_name, enc.location, sp.id, sp.species_name, assignment.created_datetime, assignment.completed_flag"
    query = db.text(query_str)
    result = session.execute(query)
    records_raw = result.fetchall()
    records = [{column: value for column, value in zip(result.keys(), record)} for record in records_raw]
    return records

def get_system_time_request_selection(session, user_id:str=None, assigned_user_id:str=None, created_date_filter:str=None, species_filter_str:str=None, override_snapshot_date:str=None):
    """
    Retrieves all selection records for the given filters and snapshot date. The selection object is joined with a number of other tables including encounter, species, and user to
    provide additional information. See method in detail to learn more about variable names assigned to columns of the other tables in the join.

    If a created_date_filter is passed, the query will be filtered only by selections which lie between the date they were created and today (or the snapshot
    date if currently in the user session).

    :param session: The database session to use for the query.
    :param user_id: The user ID to filter by (optional).
    :param assigned_user_id: The assigned user ID to filter by (optional).
    :param created_date_filter: The date to filter by for selection created date (optional) - YYYY-MM-DD HH:MM:SS.ffffff
    :param species_filter_str: The comma-separated species IDs to filter by (optional).
    :param override_snapshot_date: The snapshot date to use instead of the client session's snapshot date (optional) - YYYY-MM-DD HH:MM:SS.ffffff

    :return: A list of dictionaries representing the query results, with each dictionary containing the column names as keys.
    """
    from models import Selection
    
    snapshot_date=client_session.get('snapshot_date') if override_snapshot_date is None else override_snapshot_date

    columns = "sel.id, sel.row_start sel_row_start, sel.created_datetime sel_created_datetime, sel.selection_number, sel.row_start, sel.row_end, sel.selection_file_id, sel.contour_file_id, sel.annotation, sel.traced, sel.deactivated, sel.updated_by_id sel_updated_by_id, sel_file.filename sel_file_filename, sel_file.upload_datetime sel_file_upload_datetime, sel_file.updated_by_id sel_file_updated_by_id, contour_file.filename contour_file_filename, contour_file.upload_datetime contour_file_upload_datetime, contour_file.updated_by_id contour_file_updated_by_id, sel_file_user.id sel_file_user_id, sel_file_user.login_id sel_file_user_login_id, sel_file_user.name sel_file_user_name, contour_file_user.id contour_file_user_id, contour_file_user.name contour_file_user_name, contour_file_user.login_id contour_file_user_login_id, sp.id sp_id, sp.species_name species_name, rec.id rec_id, rec.start_time rec_start_time, enc.id enc_id, enc.encounter_name enc_encounter_name, enc.location enc_location"
    joins = "LEFT JOIN file AS sel_file ON sel_file.id = sel.selection_file_id LEFT JOIN file AS contour_file ON contour_file.id = sel.contour_file_id LEFT JOIN user AS sel_file_user ON sel_file.updated_by_id = sel_file_user.id LEFT JOIN user AS contour_file_user ON contour_file.updated_by_id = contour_file_user.id LEFT JOIN recording AS rec ON sel.recording_id = rec.id LEFT JOIN encounter AS enc ON rec.encounter_id = enc.id LEFT JOIN species AS sp ON enc.species_id = sp.id LEFT JOIN assignment ON rec.id = assignment.recording_id"
    
    if snapshot_date: query_str="SELECT {} FROM {} FOR SYSTEM_TIME AS OF '{}' AS sel".format(columns, Selection.__tablename__, snapshot_date)
    else: query_str="SELECT {} FROM {} AS sel".format(columns, Selection.__tablename__)
    query_str += " {}".format(joins)
    next_clause = "WHERE"
    if user_id: 
        query_str += " {} sel_file.updated_by_id = '{}' OR contour_file.updated_by_id = '{}' OR sel.updated_by_id = '{}'".format(next_clause, user_id, user_id, user_id)
        next_clause = "AND"
    if assigned_user_id: 
        query_str += " {} assignment.user_id = '{}'".format(next_clause, assigned_user_id)
        next_clause = "AND"
    if created_date_filter:
        query_str += " {} sel.created_datetime >= '{}'".format(next_clause, created_date_filter)
        next_clause = "AND"
    if species_filter_str is not None and species_filter_str != '':
        species_filter = species_filter_str.split(",")
        species_filter_str = ", ".join("'" + item + "'" for item in species_filter)
        query_str += " {} sp.id IN ({})".format(next_clause, species_filter_str)
        next_clause = "AND"
    query_str += f" {next_clause} sel.deactivated = 0"
    query = db.text(query_str)
    result = session.execute(query)
    # Fetch all results
    records_raw = result.fetchall()
    # Create a list of dictionaries with column names as keys
    records = [{column: value for column, value in zip(result.keys(), record)} for record in records_raw]
    
    return records

def create_system_time_request(session: sessionmaker, db_object, filters:dict=None, order_by:str=None,override_snapshot_date:datetime=None, one_result:bool=False):
    """
    Creates a database request to retrieve records from the specified database object at the current date and time, or if snapshot_date is
    defined in the user session, at that date. A different snapshot date can be provided in the method arguments aswell.

    :param session: The database session to use for the query.
    :param db_object: The database class to query (SQLAlchemy ORM).
    :param (optional) filters: A dictionary of filters to apply to the query. The keys are the column names, and the values are the filter values.
    :param (optional) order_by: A string specifying the column to order the results by. order_by is appended to the SQL parameter "ORDER BY " + order_by.
    :param (optional) override_snapshot_date: The snapshot date to use for the query. If not provided, the snapshot date from the client session is used.
    :param (optional) one_result: A boolean indicating whether to return a single result as a single database object (True) or all results as a list of database objects (False, default).
    :return: A list of database objects (if one_result=False) or a single database object (if one_result=True) representing the query results.
    """
    snapshot_date=client_session.get('snapshot_date') if override_snapshot_date is None else override_snapshot_date
    if snapshot_date: query_str="SELECT * FROM {} FOR SYSTEM_TIME AS OF '{}'".format(db_object.__tablename__, snapshot_date)
    else: query_str="SELECT * FROM {}".format(db_object.__tablename__)
    if filters:
        filter_str = " AND ".join(["{} = '{}'".format(key, value) for key, value in filters.items()])
        query_str += " WHERE " + filter_str

    if order_by:
        query_str += " ORDER BY " + order_by

    query = db.text(query_str)
    queried_db_object = session.query(db_object).from_statement(query).all()
    if one_result:
        try:
            queried_db_object = queried_db_object[0]
        except Exception as e:
            raise exception_handler.NotFoundException(f"{db_object.__tablename__} not found")

    return queried_db_object

def parse_value(key, value, prev_value):
    """
    Returns a string indicating the type of change made to a database value.
    
    Given a key, a new value and a previous value, this function returns a string
    describing the type of change. The string is in the format 'ACTION key',
    where ACTION is one of 'UPDATE', 'ADD', or 'DELETE'.

    If the value is a datetime object, the string is in the format 'UPDATE key VALUE',
    where VALUE is the new value.

    If the value is None, and the previous value is not None, the string is 'DELETE key'.
    If the value is not None, and the previous value is None, the string is 'ADD key'.
    If the value is not None, and the previous value is not None, the string is 'UPDATE key'.
    
    If the value is not a datetime object, and an error occurs while trying to compare
    the new and previous values, the string is in the format 'UPDATE key -> VALUE', where
    VALUE is the new value.

    :return: A string describing the type of change.
    """
    return_string = ""
    if type(value) == datetime or type(prev_value) == datetime:
        return_string = 'UPDATE ' + key + ' ' + str(value)
    else:
        try:
            value = value if value else None
            prev_value = prev_value if prev_value else None
            
            if value and prev_value == None:
                return_string = 'ADD ' + key
            elif value == None and prev_value:
                return_string = 'DELETE ' + key
            elif value and prev_value:
                return_string = 'UPDATE ' + key
            else:
                return_string="TEST"
        except (ValueError,AttributeError):
            return_string = 'UPDATE ' + key + ' -> ' + str(value)
    
    return return_string


def create_all_time_request(session: sessionmaker, db_class, filters=None, order_by=None):
    """
    Creates a database request to retrieve all records from the specified database object for all system time versions.

    :param session: The database session to use for the query.
    :param db_class: The database class to query (SQLAlchemy ORM).
    :param (optional) filters: A dictionary of filters to apply to the query. The keys are the column names, and the values are the filter values.
    :param (optional) order_by: A string specifying the column to order the results by. order_by is appended to the SQL parameter "ORDER BY " + order_by.

    :return: A list of dictionaries representing the query results, with each dictionary containing the column names as keys.
    """
    from models import User

    query_str="SELECT *,row_start FROM {} FOR SYSTEM_TIME ALL".format(db_class.__tablename__)
    
    if filters:
        filter_str = " AND ".join(["{} = '{}'".format(key, value) for key, value in filters.items()])
        query_str += " WHERE " + filter_str

    if order_by:
        query_str += " ORDER BY " + order_by
    
    query = db.text(query_str)
    
    result = session.execute(query)
    
    # Fetch all results
    records = result.fetchall()

    # Create a list of dictionaries with column names as keys
    recording_history = [{column: value for column, value in zip(result.keys(), record)} for record in records]
    
    # Retrieve the user objects for each updated_by_id
    for recording_history_item in recording_history:
        if recording_history_item['updated_by_id'] is not None and recording_history_item['updated_by_id'].strip() != "":
            recording_history_item['updated_by'] = session.query(User).filter_by(id=recording_history_item['updated_by_id']).first()  
        else:
            recording_history_item['updated_by'] = None 
    
    # Sort the data by 'row_start' dates
    recording_history.sort(key=lambda x: x['row_start'])
    
    prev_element = None
    for element in recording_history:
        if prev_element is None:
            element['action'] = 'CREATE'
        else:
            changes = [parse_value(key, element[key], prev_element[key]) for key in element if element[key] != prev_element.get(key) and key not in ['row_start', 'updated_by_id', 'updated_by']]
            element['action'] = changes if changes else 'No changes'
        prev_element = element

    return recording_history



def parse_snapshot_date(date_string: str):
    """
    Tries to parse a date string in one of the following formats:
    
    * %Y-%m-%d %H:%M:%S.%f
    * %Y-%m-%d %H:%M:%S
    * %Y-%m-%d %H:%M
    * %Y-%m-%dT%H:%M:%S.%f
    * %Y-%m-%dT%H:%M:%S
    * %Y-%m-%dT%H:%M
    
    If the date string is not in one of these formats, raises a ValueError with message "Invalid date format".
    """
    formats = ["%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M"]
    for date_format in formats:
        try:
            return datetime.strptime(date_string, date_format)
        except ValueError:
            pass
    raise ValueError("Invalid date format")



def parse_date(date_string: str) -> datetime:
    """
    This function takes a string and attempts to parse it as a date. This method is used 
    wherever it is necessary to read a date from a filename.
    The date can be in two formats:
    - yyyymmdd_HHMMSS
    - yymmdd-HHMMSS
    
    :param date_string: The string to parse as a date
    :type date_string: str
    :return: The parsed date
    """
    import re
    match = re.search(r'(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})', date_string)
    if match:
        year = match.group(1)
        month = match.group(2)
        day = match.group(3)
        hour = match.group(4)
        minute = match.group(5)
        second = match.group(6)
        date_string = f"{day}/{month}/{year} {hour}:{minute}:{second}"
        date = datetime.strptime(date_string, '%d/%m/%Y %H:%M:%S')
    if not match:
        match = re.search(r'(\d{2})(\d{2})(\d{2})-(\d{2})(\d{2})(\d{2})', date_string)
        if match:
            year = match.group(1)
            month = match.group(2)
            day = match.group(3)
            hour = match.group(4)
            minute = match.group(5)
            second = match.group(6)
            date_string = f"{day}/{month}/{year} {hour}:{minute}:{second}"
            date = datetime.strptime(date_string, '%d/%m/%y %H:%M:%S')

    return date