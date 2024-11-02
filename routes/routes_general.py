# Standard library imports
import hashlib
import os
import zipfile
import traceback
from jinja2 import Environment


from flask import current_app, Blueprint, flash,get_flashed_messages, jsonify, redirect,render_template,request, send_file,session, url_for, send_from_directory
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timedelta

import werkzeug

# Local application imports
from database_handler import get_session, Session, require_live_session,exclude_role_1,exclude_role_2,exclude_role_3,exclude_role_4
from models import *
from exception_handler import *

# Third-party imports
from flask import (Flask, flash, get_flashed_messages, jsonify, redirect,
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


routes_general = Blueprint('general', __name__)


@routes_general.errorhandler(OperationalError)
def handle_operational_error(ex):
    logger.exception('Operational error')
    return render_template('operational-error.html')

@routes_general.errorhandler(Exception)
def handle_error(ex):
    logger.exception('Exception')
    return render_template('general-error.html', error_code=404, error_message=str(ex), current_timestamp_utc=datetime.utcnow(), goback_link='/home', goback_message="Home")


# 404 Error Handler
@routes_general.errorhandler(404)
def page_not_found(e):
    logger.warning('Page not found: ' + str(e))
    return "Page not found. Please check the URL and try again.", 404

# 405 Error Handler
@routes_general.errorhandler(405)
def method_not_allowed(e):
    logger.warning('Method not allowed: ' + str(e))
    return "Method not allowed. Please check the request method and try again.", 405

# 500 Error Handler
@routes_general.errorhandler(500)
def internal_server_error(e):
    logger.critical('Internal server error: ' + str(e))
    return "Internal server error. Please try again later.", 500

# 502 Error Handler
@routes_general.errorhandler(502)
def bad_gateway(e):
    logger.critical('Bad gateway: ' + str(e))
    return "Bad gateway. Please try again later.", 502

# 503 Error Handler
@routes_general.errorhandler(503)
def service_unavailable(e):
    logger.critical('Service unavailable: ' + str(e))
    return "Service unavailable. Please try again later.", 503

# 504 Error Handler
@routes_general.errorhandler(504)
def gateway_timeout(e):
    logger.critical('Gateway timeout: ' + str(e))
    return "Gateway timeout. Please try again later.", 504

@routes_general.errorhandler(CriticalException)
def critical_exception(e):
    logger.exception('Critical exception')
    return render_template('general-error.html', error_message=str(e), current_timestamp_utc=datetime.utcnow(), goback_link=request.referrer, goback_message="Back")

@routes_general.errorhandler(NotFoundException)
def not_found(e):
    logger.warning('Not found exception: ' + str(e))
    return render_template('error.html', error_code=404, error=str(e) + "<br>" + str(e.details), goback_link=request.referrer, goback_message="Go Back")

@routes_general.errorhandler(Exception)
def general_exception(e):
    logger.exception('General exception')
    return render_template('general-error.html', error_message=str(e), current_timestamp_utc=datetime.utcnow(), goback_link=request.referrer, goback_message="Back")

@routes_general.route('/favicon.ico')
def favicon():
    """For the Web App's favicon"""
    return send_from_directory('resources',
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

@routes_general.route('/file-details/<file_id>', methods=['GET'])
def get_file_details(file_id):
    """
    A route to render a template to see generic information on a particular file.
    This includes information like the file's name, path, original name etc. An
    argument can be passed in the request, file_details, which is displayed at
    the top of the page.

    :param file_id: the ID of the file to render information for
    :type file_id: str 
    """
    file_details = request.args.get('file_details')
    if not file_details: file_details = ''
    with get_session() as session:
        file_obj = session.query(File).filter_by(id=file_id).first()
        return render_template('file-info.html', file=file_obj, file_details=file_details, redirect_link=request.referrer)


@routes_general.route('/enter-snapshot-date-in-session', methods=['GET'])
def enter_snapshot_date_in_session():
    """
    Enter the snapshot date into the session. This works well
    to enter the snapshot date into the session so that it can be
    passed to new requests.
    """
    snapshot_date = request.args.get('snapshot_date')
    client_session['snapshot_date'] = snapshot_date
    return redirect(request.referrer)

def remove_snapshot_date_from_url(url):
    """
    Remove the argument snapshot_date from a url parameter. This works well
    to exit out of archive mode so that the argument is no longer passed to
    new requests.
    """
    # Split the URL into base URL and query parameters
    base_url, params = url.split('?', 1) if '?' in url else (url, '')
    
    # Split the query parameters into individual parameters
    param_list = params.split('&')
    
    # Remove the snapshot_date parameter
    updated_params = [param for param in param_list if not param.startswith('snapshot_date=')]
    
    # Reconstruct the URL without the snapshot_date parameter
    updated_url = base_url + ('?' + '&'.join(updated_params) if updated_params else '')
    
    return updated_url

@routes_general.route('/reset-snapshot-in-session-with-link', methods=['GET','POST'])
def reset_snapshot_in_session_with_link():
    """
    Remove the snapshot date from the session, therefore exiting out of archive mode. 
    After the snapshot date has been removed, redirect the user to a link provided
    in a form element with the POST request submission, redirect_link.
    """
    redirect_link = request.form.get('redirect_link')
    client_session['snapshot_date'] = None
    return redirect(remove_snapshot_date_from_url(redirect_link))

@routes_general.route('/reset-snapshot-in-session', methods=['GET','POST'])
def reset_snapshot_in_session():
    """
    Remove the snapshot date from the session, therefore exiting out of archive mode.
    Once complete redirect the user back to the page that they were on.
    """
    client_session['snapshot_date']=None
    return redirect(remove_snapshot_date_from_url(request.referrer))

@routes_general.route('/resources/<path:filename>')
def serve_resource(filename):
    """
    Serve a file from the 'resources' directory (for resources such as images).
    """
    return send_from_directory('resources', filename)

@routes_general.route('/static/js/<path:filename>')
def serve_script(filename):
    """
    Serve a file from the 'static/js' directory (for JS).
    """
    return send_from_directory('static/js', filename)

@routes_general.route('/static/css/<path:filename>')
def serve_style(filename):
    """
    Serve a file from the 'static/css' directory (for CSS).
    """
    return send_from_directory('static/css', filename)

@routes_general.route('/')
def index():
    """
    Redirect user from root to home directory.
    """
    return redirect(url_for('general.home', user=current_user))

@routes_general.route('/api/users')
def search_users():
    """
    API endpoint to search users based on the search term.
    """
    search_term = request.args.get('search')
    with get_session() as session:
        users = session.query(User).filter(
            or_(
                User.name.ilike(f'%{search_term}%'),
                User.login_id.ilike(f'%{search_term}%')
            ),
            User.is_temporary == False
        ).all()
        user_list = [{'id': user.id, 'name': user.name, 'login_id': user.login_id} for user in users]
        return jsonify({'users': user_list})

@routes_general.route('/home') 
@login_required
def home():
    """
    Route for the home page.
    """
    with get_session() as session:
        result = session.query(Recording, Assignment). \
            join(Assignment, Assignment.recording_id == Recording.id). \
            filter(Assignment.user_id == current_user.id). \
            order_by((Recording.status == "On Hold").desc()). \
            order_by(Assignment.completed_flag). \
            order_by(Assignment.created_datetime.desc()). \
            all()
        recordings = [{'recording': recording, 'assignment': assignment} for recording, assignment in result]
        return render_template('home.html', user=current_user, recordings=recordings)


@routes_general.route('/ping', methods=['GET'])
def ping():
    # This endpoint could be enhanced to log pings or check connection status
    return jsonify(status='alive')


@routes_general.route('/upload_chunk', methods=['POST'])
def upload_chunk():
    filename = request.form['filename']
    chunk = request.files['chunk']

    if str(filename).endswith('.blob'):
        filename = filename[:-5]
    
    extension = filename.split('.')[-1]
    filename_no_extension = filename[:-len(extension)-1]
    
    chunk_index = int(request.form['chunk_index'])
    num_chunks = int(request.form['num_chunks'])
    
    with database_handler.get_session() as session:
        if 'file_id' not in request.form:
            file = File()
            file.temp = True
            session.add(file)
            file.insert_path_and_filename(session, chunk, os.path.join(str(current_user.id), str(uuid.uuid4().hex)), filename_no_extension, override_extension=extension, root_path=database_handler.get_tempdir())
            session.commit()
            file_id = file.id
        else:
            file_id = request.form['file_id']  # Get the file ID from the request
            file = session.query(File).filter_by(id=file_id).first()
            file.append_chunk(chunk)
        
        # Return a JSON response with the progress
        progress = (chunk_index + 1) / num_chunks * 100
        return jsonify({'progress': progress, 'message':f"Uploaded chunk {chunk_index+1} out of {num_chunks}.", 'file_id': file_id})


@routes_general.route('/upload', methods=['POST'])
def upload():
    # Get the uploaded file from the temporary directory
    file_id = request.form['file_id']
    with database_handler.get_session() as session:
        file = session.query(File).filter_by(id=file_id).first()
        file_path = file.get_full_absolute_path()

        # Save the file to a permanent location
        #permanent_file_path = os.path.join('permanent_uploads', filename)
        #os.rename(file_path, permanent_file_path)

        return 'File uploaded successfully! Found ' + str(file_path) + ": " + str(os.path.exists(file_path))
