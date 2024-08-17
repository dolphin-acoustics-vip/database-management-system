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