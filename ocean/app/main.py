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

# Standard library imports
import os
from datetime import datetime

# Third-party imports
from jinja2 import Environment
from flask import Flask, flash, redirect, render_template, request, url_for, session as client_session, g
from flask_login import LoginManager, login_user,login_required, current_user, login_manager, logout_user
from flask_restx import Api

# Local application imports
from . import models
from . import exception_handler
from .logger import logger
from . import database_handler
from . import filespace_handler
from .routes.routes_general import routes_general
from .routes.routes_admin import routes_admin
from .routes.routes_selection import routes_selection
from .routes.routes_encounter import routes_encounter
from .routes.routes_recording import routes_recording
from .routes.routes_encounter import routes_encounter
from .routes.routes_datahub import routes_datahub
from .routes.routes_healthcentre import routes_healthcentre
from .routes.routes_filespace import routes_filespace 
from .routes.api import blueprint as api

def check_interfaces():
    """
    Checks the database for all interfaces by instantiating an instance of each model.
    If any interface is missing a TypeError will be raised.
    """
    recording_platform = models.RecordingPlatform()
    user = models.User()
    recording = models.Recording()
    assignment = models.Assignment()
    data_source = models.DataSource()
    encounter = models.Encounter()
    species = models.Species()
    selection = models.Selection(recording)
    file = models.File()
    role = models.Role()
    

def check_file_space():
    FILE_SPACE_PATH = os.environ.get('OCEAN_FILESPACE_PATH')

    if FILE_SPACE_PATH == None or FILE_SPACE_PATH.strip() == '':
        raise(exception_handler.CriticalException(f"File space path not found in environment variable 'OCEAN_FILESPACE_PATH'. Cannot proceed."))
    elif not os.path.exists(FILE_SPACE_PATH):
        raise(exception_handler.CriticalException(f"File space path '{FILE_SPACE_PATH}' does not exist. Cannot proceed."))
    else:
        return f"Assigned file space '{FILE_SPACE_PATH}'"


def create_app(config_class):
    app = Flask(__name__)
    check_interfaces()
    ROUTE_PREFIX = '/ocean'

    # Set up a custom login manager for the web app
    login_manager = LoginManager()
    login_manager.init_app(app)

    app.config.from_object(config_class)

    # Set up user loader for the login manager
    @login_manager.user_loader
    def load_user(user_id):
        return models.User.query.get(user_id) 

    @app.before_request
    def sso_login():
        # Retrieve email from environment
        email = request.environ.get('HTTP_EPPN')
        

        override = os.environ.get('OCEAN_SSO_OVERRIDE', '').lower()
        if override != None and override != '':
            email = override


        # Skip if user is already authenticated
        if current_user.is_authenticated and current_user.login_id == email:
            return
            
        if email:
            # Query for the user based on email
            user = models.User.query.filter_by(login_id=email.lower()).first()
            g.user = user 
            if user:
                if not user.is_active:
                   return "Your account has been deactivated. Please contact your administrator.", 403
                days_until_expiry = (user.expiry - datetime.now().date()).days
                if user.expiry < datetime.now().date():
                    return "Your account has expired. Please contact your administrator.", 403
                elif days_until_expiry <= 30:
                    flash(f'Your account will be deactivated in {days_until_expiry} days. Please contact your administrator to prevent this.', 'warning')
                # If user exists in the database, log them in
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

    # create_database_script = ''
    # if config_class.__name__ == 'TestingConfig':
    #     create_database_script = 'create_database.sql'
    # else:
    #     create_database_script = 'script_run.sql'

    
    db = database_handler.init_db(app)
    database_handler.init_api(api)
    filespace_handler.clean_directory(database_handler.get_file_space_path())

    # Register blueprints and error handlers
    app.register_blueprint(routes_general, url_prefix=ROUTE_PREFIX)
    app.register_blueprint(routes_admin, url_prefix=ROUTE_PREFIX)
    app.register_blueprint(routes_encounter, url_prefix=ROUTE_PREFIX)
    app.register_blueprint(routes_recording, url_prefix=ROUTE_PREFIX)
    app.register_blueprint(routes_selection, url_prefix=ROUTE_PREFIX)
    app.register_blueprint(routes_datahub, url_prefix=ROUTE_PREFIX)
    app.register_blueprint(routes_healthcentre, url_prefix=ROUTE_PREFIX)
    app.register_blueprint(routes_filespace, url_prefix=ROUTE_PREFIX)
    
    app.register_blueprint(api, url_prefix=ROUTE_PREFIX + "/api/")

    try:
        logger.info(check_file_space())
    except exception_handler.CriticalException as e:
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

    import MySQLdb
    @app.errorhandler(MySQLdb.OperationalError)
    def handle_mysql_error(ex):
        logger.error(str(ex))
        return "Database not functional."
    

    @app.errorhandler(exception_handler.DoesNotExistError)
    def handle_dne_error(ex):
        logger.warning(str(ex))
        return render_template('general-error.html', error_code=404, error_message=str(ex), current_timestamp_utc=datetime.utcnow(), goback_link=request.referrer, goback_message="Go back")


    @app.errorhandler(exception_handler.CriticalException)
    def handle_critical_error(ex):
        logger.error(ex)
        return render_template('general-error.html', error_code=404, error_message="Internal server error", current_timestamp_utc=datetime.utcnow(), goback_link=request.referrer, goback_message="Go back")

    @app.errorhandler(Exception)
    def handle_error(ex):
        exception_handler.handle_exception(exception=ex)
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
        return "Internal server error(s). Please try again later.", 500

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


