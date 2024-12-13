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
from datetime import datetime
import os
import uuid

# Local application imports
from .. import database_handler
from .. import models
from .. import exception_handler
from .. import filespace_handler
from ..logger import logger

# Third-party imports
from flask import Blueprint, flash, get_flashed_messages, jsonify, redirect, render_template, request, send_file, url_for, send_from_directory, session as client_session, g
from flask_login import login_required, current_user
from sqlalchemy import or_
from sqlalchemy.exc import OperationalError

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

@routes_general.errorhandler(exception_handler.CriticalException)
def critical_exception(e):
    logger.exception('Critical exception')
    return render_template('general-error.html', error_message=str(e), current_timestamp_utc=datetime.utcnow(), goback_link=request.referrer, goback_message="Back")

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
    with database_handler.get_session() as session:
        file_obj = session.query(models.File).filter_by(id=file_id).first()
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
    with database_handler.get_session() as session:
        users = session.query(models.User).filter(
            or_(
                models.User.name.ilike(f'%{search_term}%'),
                models.User.login_id.ilike(f'%{search_term}%')
            ),
            models.User.is_temporary == False
        ).all()
        user_list = [{'id': user.id, 'name': user.name, 'login_id': user.login_id} for user in users]
        return jsonify({'users': user_list})

@routes_general.route('/home') 
@login_required
def home():
    """
    Route for the home page.
    """
    with database_handler.get_session() as session:
        result = session.query(models.Recording, models.Assignment). \
            join(models.Assignment, models.Assignment.recording_id == models.Recording.id). \
            filter(models.Assignment.user_id == current_user.id). \
            order_by((models.Recording.status == "On Hold").desc()). \
            order_by(models.Assignment.completed_flag). \
            order_by(models.Assignment.created_datetime.desc()). \
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
    file_chunk = request.files['chunk']

    if str(filename).endswith('.blob'):
        filename = filename[:-5]
    
    extension = filename.split('.')[-1]
    # filename_no_extension = filename[:-len(extension)-1]
    
    chunk_index = int(request.form['chunk_index'])
    num_chunks = int(request.form['num_chunks'])
    
    # Generate a unique file_id if the chunk_index is 0 (i.e. the first chunk).
    # Otherwise expect a file_id to be provided in the request form - and if not raise an error.
    if 'file_id' not in request.form and chunk_index != 0:
        raise ValueError('A chunk upload with chunk_index != 0 requires a file_id.')
    file_id = request.form['file_id'] if chunk_index != 0 else str(uuid.uuid4().hex)
    path = filespace_handler.get_path_to_temporary_file(file_id, filename)
    
    chunk_size = 1024 * 1024  # 1MB chunks
    with open(path, 'wb' if chunk_index == 0 else 'ab') as f:
        while True:
            chunk = file_chunk.stream.read(chunk_size)
            if chunk: f.write(chunk)
            else: break

    progress = (chunk_index + 1) / num_chunks * 100

    return jsonify({'progress': progress, 'message':f"Uploaded chunk {chunk_index+1} out of {num_chunks}.", 'file_id': file_id, 'filename': filename})


@routes_general.route('/upload', methods=['POST'])
def upload():
    # Get the uploaded file from the temporary directory
    file_id = request.form['file_id']
    with database_handler.get_session() as session:
        file = session.query(models.File).filter_by(id=file_id).first()
        file_path = file.get_full_absolute_path()

        return 'File uploaded successfully! Found ' + str(file_path) + ": " + str(os.path.exists(file_path))
