import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import joinedload, sessionmaker
import sqlalchemy

# Create a Flask app
app = Flask(__name__)
app.secret_key = 'kdgnwinhuiohji3275y3hbhjex?1'

# Configure the database connection using SQLAlchemy and MariaDB
app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+mysqldb://{os.environ['STADOLPHINACOUSTICS_USER']}:{os.environ['STADOLPHINACOUSTICS_PASSWORD']}@{os.environ['STADOLPHINACOUSTICS_HOST']}/{os.environ['STADOLPHINACOUSTICS_DATABASE']}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Define the file space folder and get the Google API key from a file
FILE_SPACE_PATH = ''
if os.path.exists('file_space_path.txt'):
    with open('file_space_path.txt', 'r') as f:
        FILE_SPACE_PATH = f.read()
GOOGLE_API_KEY = ''
if os.path.exists('google_api_key.txt'):
    with open('google_api_key.txt', 'r') as f:
        GOOGLE_API_KEY = f.read()

# Initialize the SQLAlchemy database
db = SQLAlchemy(session_options={"autoflush": False})
db.init_app(app)

# Create the engine and session within a route or a view function
with app.app_context():
    engine = db.get_engine()
    Session = sessionmaker(bind=engine, autoflush=False)

def parse_alchemy_error(error):
    """
    Parse SQLAlchemy errors and return a human-readable error messages.

    Parameters:
    error (sqlalchemy.exc.Error): The SQLAlchemy error to be parsed.

    Returns:
    A human-readable error message based on the type of SQLAlchemy error.
    """
    raise error
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