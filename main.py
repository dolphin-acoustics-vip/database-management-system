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
from flask_login import login_user,login_required, current_user, login_manager, logout_user
from flask import g
import sqlalchemy

from routes.routes_general import routes_general
from routes.routes_admin import routes_admin
from routes.routes_selection import routes_selection
from routes.routes_encounter import routes_encounter
from routes.routes_recording import routes_recording
from routes.routes_encounter import routes_encounter
from routes.routes_datahub import routes_datahub
from routes.routes_healthcentre import routes_healthcentre
from routes.routes_filespace import routes_filespace

# Local application imports
from models import *
from exception_handler import NotFoundException, CriticalException
from logger import logger

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

    ROUTE_PREFIX = '/ocean'

    if config_class is None:
        config_class = os.getenv('FLASK_CONFIG', 'config.DevelopmentConfig')
    app.config.from_object(config_class)

    # Set up a custom login manager for the web app
    login_manager = LoginManager()
    login_manager.init_app(app)

    # Set up user loader for the login manager
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(user_id) 

    @app.before_request
    def sso_login():
        # Retrieve email from environment
        email = request.environ.get('HTTP_EPPN')
        email = 'admin@testmail.com' #THIS CANNOT BE LEFT IN THE PRODUCTION ENVIRONMENT

        # Skip if user is already authenticated
        if current_user.is_authenticated and current_user.login_id == email:
            return
            
        if email:
            # Query for the user based on email
            user = User.query.filter_by(login_id=email).first()
            g.user = user 

            if not user.is_active:
                return "Your account has been deactivated. Please contact your administrator.", 403
            days_until_expiry = (user.expiry - datetime.now().date()).days
            if user.expiry < datetime.now().date():
                return "Your account has expired. Please contact your administrator.", 403
            elif days_until_expiry <= 30:
                flash(f'Your account will be deactivated in {days_until_expiry} days. Please contact your administrator to prevent this.', 'warning')
            # If user exists in the database, log them in
            if user:
                login_user(user)
            else:
                # Redirect or handle users who are not in the database
                return f"User '{email}' not given access permissions. Please contact your administrator.", 403
        else:
            return "Unable to access single-sign-on service", 403 # Redirect if no SSO email is found
        
    @app.route('/logout')
    def logout():
        logout_user()
        client_session.clear()
        return redirect(url_for('general.home'))

    create_database_script = ''
    if config_class == 'config.TestingConfig':
        create_database_script = 'create_database.sql'
    else:
        create_database_script = 'script_run.sql'

    db = init_db(app, run_script=create_database_script)

    # Register blueprints and error handlers
    app.register_blueprint(routes_general, url_prefix=ROUTE_PREFIX)
    app.register_blueprint(routes_admin, url_prefix=ROUTE_PREFIX)
    app.register_blueprint(routes_encounter, url_prefix=ROUTE_PREFIX)
    app.register_blueprint(routes_recording, url_prefix=ROUTE_PREFIX)
    app.register_blueprint(routes_selection, url_prefix=ROUTE_PREFIX)
    app.register_blueprint(routes_datahub, url_prefix=ROUTE_PREFIX)
    app.register_blueprint(routes_healthcentre, url_prefix=ROUTE_PREFIX)
    app.register_blueprint(routes_filespace, url_prefix=ROUTE_PREFIX)

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



    @app.errorhandler(OperationalError)
    def handle_operational_error(ex):
        logger.exception('Operational error')
        return render_template('operational-error.html')

    @app.errorhandler(Exception)
    def handle_error(ex):
        logger.exception('Exception')
        return render_template('general-error.html', error_code=404, error_message=str(ex), current_timestamp_utc=datetime.utcnow(), goback_link='/home', goback_message="Home")

    # 404 Error Handler
    @app.errorhandler(404)
    def page_not_found(e):
        logger.warning('Page not found: ' + str(e))
        return "Page not found. Please check the URL and try again.", 404

    # 405 Error Handler
    @app.errorhandler(405)
    def method_not_allowed(e):
        logger.warning('Method not allowed: ' + str(e))
        return "Method not allowed. Please check the request method and try again.", 405

    # 500 Error Handler
    @app.errorhandler(500)
    def internal_server_error(e):
        logger.critical('Internal server error: ' + str(e))
        return "Internal server error. Please try again later.", 500

    # 502 Error Handler
    @app.errorhandler(502)
    def bad_gateway(e):
        logger.critical('Bad gateway: ' + str(e))
        return "Bad gateway. Please try again later.", 502

    # 503 Error Handler
    @app.errorhandler(503)
    def service_unavailable(e):
        logger.critical('Service unavailable: ' + str(e))
        return "Service unavailable. Please try again later.", 503

    # 504 Error Handler
    @app.errorhandler(504)
    def gateway_timeout(e):
        logger.critical('Gateway timeout: ' + str(e))
        return "Gateway timeout. Please try again later.", 504

    @app.errorhandler(NotFoundException)
    def not_found(e):
        logger.warning('Not found exception: ' + str(e))
        return render_template('error.html', error_code=404, error=str(e), goback_link='/home', goback_message="Home")


    



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