# Standard library imports
import os
import zipfile
import traceback
from jinja2 import Environment


# Third-party imports
from flask import (abort, Flask, flash, get_flashed_messages, jsonify, redirect,
                   render_template, request, send_file, url_for,
                   send_from_directory)
from flask import session as client_session
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError, OperationalError

from sqlalchemy.orm import joinedload, sessionmaker
from flask_login import LoginManager
from flask_login import login_user,login_required, current_user, login_manager
from flask import g
import sqlalchemy

from routes.routes_general import routes_general
from routes.routes_admin import routes_admin
from routes.routes_selection import routes_selection
from routes.routes_encounter import routes_encounter
from routes.routes_auth import routes_auth
from routes.routes_recording import routes_recording
from routes.routes_encounter import routes_encounter
from routes.routes_datahub import routes_datahub
from routes.routes_healthcentre import routes_healthcentre

# Local application imports
from models import *
from exception_handler import NotFoundException, CriticalException
from logger import logger

# main_app.py (your main file)

from flask import Flask
from database_handler import init_db, get_session
from sqlalchemy import event
from flask_login import current_user


def check_file_space():
    # Define the file space folder and get the Google API key from a file
    FILE_SPACE_FILENAME = 'file_space_path.txt'
    FILE_SPACE_PATH = ''
    if os.path.exists(FILE_SPACE_FILENAME):
        with open(FILE_SPACE_FILENAME, 'r') as f:
            FILE_SPACE_PATH = f.read()
            if FILE_SPACE_PATH == None or FILE_SPACE_PATH.strip() == '':
                raise(CriticalException(f"File space path found in '{FILE_SPACE_FILENAME}' however the file is empty. Cannot proceed."))
            elif not os.path.exists(FILE_SPACE_PATH):
                raise(CriticalException(f"File space path found in '{FILE_SPACE_FILENAME}' however the path '{FILE_SPACE_PATH}' does not exist. Cannot proceed."))
            else:
                return f"Assigned file space '{FILE_SPACE_PATH}'"
    else:
        raise(CriticalException(f"File space path configuration file not found in '{FILE_SPACE_FILENAME}'"))



def create_app(config_class=None):
    app = Flask(__name__)

    if config_class is None:
        config_class = os.getenv('FLASK_CONFIG', 'config.DevelopmentConfig')
    app.config.from_object(config_class)

    create_database_script = ''
    if config_class == 'config.TestingConfig':
        create_database_script = 'create_database.sql'

    db = init_db(app, create_database=create_database_script)

    # Register blueprints and error handlers
    app.register_blueprint(routes_general)
    app.register_blueprint(routes_admin)
    app.register_blueprint(routes_encounter)
    app.register_blueprint(routes_recording)
    app.register_blueprint(routes_selection)
    app.register_blueprint(routes_auth)
    app.register_blueprint(routes_datahub)
    app.register_blueprint(routes_healthcentre)

    try:
        logger.info(check_file_space())
    except CriticalException as e:
        logger.fatal(str(e))
        return

    env = Environment()
    env.globals['getattr'] = getattr


    @app.before_request
    def before_request():
        """
        Store the logged in user information in each request.
        """
        g.user = current_user

    @app.errorhandler(403)
    def forbidden(e):
        logger.warning('Route forbidden: ' + str(e))
        return render_template('unauthorized.html', user=current_user), 403

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


    return app

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

if __name__ == '__main__':
    app = create_app('config.DevelopmentConfig')
    if app is None:
        logger.fatal('Exiting program...')
        exit(1)
    logger.info('Starting application')
    app.run()