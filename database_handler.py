# Standard library imports
import os, uuid
from flask import Flask, session, redirect, render_template, session as client_session, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import joinedload, sessionmaker
import sqlalchemy
from flask_login import LoginManager, login_user, login_required,  current_user, login_manager
from functools import wraps
from sqlalchemy import event
from flask_login import login_user,login_required, current_user, login_manager
from jinja2 import Environment
import exception_handler, datetime

env = Environment()
env.globals['getattr'] = getattr

DATA_DIR = 'data'
TEMP_DIR = 'tempdir'

# Define the file space folder and get the Google API key from a file
FILE_SPACE_PATH = ''
if os.path.exists('file_space_path.txt'):
    with open('file_space_path.txt', 'r') as f:
        FILE_SPACE_PATH = f.read()

# TODO: remove
GOOGLE_API_KEY = ''
if os.path.exists('google_api_key.txt'):
    with open('google_api_key.txt', 'r') as f:
        GOOGLE_API_KEY = f.read()

def get_file_space_path():
    return os.path.join(FILE_SPACE_PATH, DATA_DIR)

def get_tempdir():
    if not os.path.exists(os.path.join(FILE_SPACE_PATH, TEMP_DIR)):
        os.makedirs(os.path.join(FILE_SPACE_PATH, TEMP_DIR))
    return os.path.join(FILE_SPACE_PATH, TEMP_DIR)


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


# Create a Flask app
app = Flask(__name__)

# TODO: use an actual secret key
app.secret_key = 'kdgnwinhuiohji3275y3hbhjex?1'

# Configure the database connection using SQLAlchemy and MariaDB
app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+mysqldb://{os.environ['STADOLPHINACOUSTICS_USER']}:{os.environ['STADOLPHINACOUSTICS_PASSWORD']}@{os.environ['STADOLPHINACOUSTICS_HOST']}/{os.environ['STADOLPHINACOUSTICS_DATABASE']}"

# USED FOR THE Docker TEST ENVIRONMENT:
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqldb://root:test123@127.0.0.1:3306/test_database'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the SQLAlchemy database
db = SQLAlchemy(session_options={"autoflush": False})
db.init_app(app)

# Create the engine and session within a route or a view function
with app.app_context():
    engine = db.get_engine()
    Session = sessionmaker(bind=engine, autoflush=False)
    
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



# A number of annotations that can be applied to flask route methods to restrict access to certain
# user access level permissions.

def exclude_role_1(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if current_user.is_authenticated and current_user.role_id != 1:
            return func(*args, **kwargs)
        else:
            return render_template("unauthorized.html", user=current_user)
    return wrapper
                   
def exclude_role_2(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if current_user.is_authenticated and current_user.role_id != 2:
            return func(*args, **kwargs)
        else:
            return render_template("unauthorized.html", user=current_user)
    return wrapper

def exclude_role_3(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if current_user.is_authenticated and current_user.role_id != 3:
            return func(*args, **kwargs)
        else:
            return render_template("unauthorized.html", user=current_user)
    return wrapper

def exclude_role_4(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if current_user.is_authenticated and current_user.role_id != 4:
            return func(*args, **kwargs)
        else:
            return render_template("unauthorized.html", user=current_user)
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



# Setup user login
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.init_app(app)
@login_manager.user_loader
def load_user(user_id: str):
    """
    Retrieve the user relation for the database for a particular user_id. Return value is an 
    instance of the User class, or None if the user_id is not found.
    """
    from sqlalchemy.exc import OperationalError
    try:
        from models import User
        # Since the user_id is just the primary key of the user table, use it in the query for the user
        return User.query.get(uuid.UUID(user_id))
    except OperationalError:
        return None


def parse_alchemy_error(error: sqlalchemy.exc.IntegrityError) -> str:
    """
    Parse SQLAlchemy errors and return a human-readable message which can be displayed in the UI
    where necessary. This method can parse database errors such as illegal duplicates, null values,
    foreign key constraints, operational errors, and programming errors. Where an error is
    unrecognised, the default sqlalchemy error message is returned with a prefix
    """
    print(error)
    if isinstance(error, sqlalchemy.exc.OperationalError) or isinstance(error, sqlalchemy.exc.IntegrityError) or isinstance(error, sqlalchemy.exc.ProgrammingError):
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





def get_system_time_request_recording(session, user_id=None, assigned_user_id=None, created_date_filter=None, species_filter_str=None, override_snapshot_date=None):
    from models import Recording
    snapshot_date=client_session.get('snapshot_date') if override_snapshot_date is None else override_snapshot_date

    columns = "rec.id, rec.created_datetime, rec.start_time, rec.status, enc.id enc_id, enc.encounter_name enc_encounter_name, enc.location enc_location, sp.id sp_id, sp.species_name sp_species_name, assignment.created_datetime assignment_created_datetime, assignment.completed_flag assignment_completed_flag, COUNT(CASE WHEN sel.traced = 1 AND sel.deactivated = 0 THEN sel.id END) traced_count, COUNT(CASE WHEN sel.deactivated = 1 THEN sel.id END) deactivated_count, COUNT(CASE WHEN sel.traced IS NULL AND sel.deactivated = 0 THEN sel.id END) untraced_count, assignment_user.id assignment_user_id, assignment_user.name assignment_user_name, assignment_user.login_id assignment_user_login_id"

    joins = "LEFT JOIN encounter AS enc ON rec.encounter_id = enc.id LEFT JOIN species AS sp ON enc.species_id = sp.id LEFT JOIN assignment ON rec.id = assignment.recording_id LEFT JOIN user AS assignment_user ON assignment.user_id = assignment_user.id LEFT JOIN selection AS sel ON rec.id = sel.recording_id"

    # COUNT(sel_untraced.id) untraced_count, 
    # LEFT JOIN selection AS sel_untraced ON rec.id = sel_untraced.recording_id AND sel_untraced.traced IS NULL AND sel_untraced.deactivated = 0
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
    print(query)
    result = session.execute(query)
    # Fetch all results
    records_raw = result.fetchall()
    # Create a list of dictionaries with column names as keys
    records = [{column: value for column, value in zip(result.keys(), record)} for record in records_raw]
    
    return records

def get_system_time_request_with_joins(session, user_id=None, assigned_user_id=None, created_date_filter=None, species_filter_str=None, override_snapshot_date=None):
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


def page_not_found(error,redirect):
    snapshot_date = client_session.get('snapshot_date')
    return render_template('error.html', error_code=404, error=error, goback_link=redirect, goback_message="Home", snapshot_date=snapshot_date, user=current_user)

def create_system_time_between_request(session, db_object, start_date, end_date, filters=None, order_by=None):
    from models import User

    query_str="SELECT *,row_start,row_end FROM {} FOR SYSTEM_TIME BETWEEN '{}' AND '{}'".format(db_object.__tablename__, start_date, end_date)
    if filters:
        filter_str = " AND ".join(["{} = '{}'".format(key, value) for key, value in filters.items()])
        query_str += " WHERE " + filter_str

    if order_by:
        query_str += " ORDER BY " + order_by

    
    query = db.text(query_str)
    print(query)
    result = session.execute(query)
    
    # Fetch all results
    records = result.fetchall()

    # Create a list of dictionaries with column names as keys
    recording_history = [{column: value for column, value in zip(result.keys(), record)} for record in records]
    print('I GOT HERE')
    for recording_history_item in recording_history:
        if recording_history_item['updated_by_id'] is not None and recording_history_item['updated_by_id'].strip() != "":
            print('QUERY USER')
            print(session.query(User).filter_by(id=recording_history_item['updated_by_id']).first() )
            recording_history_item['updated_by'] = session.query(User).filter_by(id=recording_history_item['updated_by_id']).first()  
        else:
            recording_history_item['updated_by'] = None 
    # Sort the data by 'row_start' dates
    recording_history.sort(key=lambda x: x['row_start'])
    


    return recording_history


def create_system_time_request(session, db_object, filters=None, order_by=None,override_snapshot_date=None, one_result=False):
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



def create_all_time_request(session, db_object, filters=None, order_by=None):
    from models import User
    # Write the raw SQL query to select all records from the recording table for all system time versions
    # Execute the raw SQL query with the recording_id parameter
    
    query_str="SELECT *,row_start FROM {} FOR SYSTEM_TIME ALL".format(db_object.__tablename__)
    
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
    for recording_history_item in recording_history:
        if recording_history_item['updated_by_id'] is not None and recording_history_item['updated_by_id'].strip() != "":
            recording_history_item['updated_by'] = session.query(User).filter_by(id=recording_history_item['updated_by_id']).first()  
        else:
            recording_history_item['updated_by'] = None 
    # Sort the data by 'row_start' dates
    recording_history.sort(key=lambda x: x['row_start'])
    
    def parse_value(key, value, prev_value):
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
    prev_element = None
    for element in recording_history:
        if prev_element is None:
            element['action'] = 'CREATE'
        else:
            changes = [parse_value(key, element[key], prev_element[key]) for key in element if element[key] != prev_element.get(key) and key not in ['row_start', 'updated_by_id', 'updated_by']]
            element['action'] = changes if changes else 'No changes'
        prev_element = element
    #missing_selections, error_msg = recording.validate_selection_table(session)
    #missing_selections=[]
    #error_msg=""

    return recording_history
