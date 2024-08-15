# Standard library imports
import os
import zipfile

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

# Local application imports
from db import Session, FILE_SPACE_PATH, GOOGLE_API_KEY, app
from models import *
from routes.routes_admin import routes_admin
from routes.routes_encounter import routes_encounter
from routes.routes_recording import routes_recording
from routes.routes_selection import routes_selection
from routes.routes_contour import routes_contour
from routes.routes_auth import routes_auth
from routes.routes_datahub import routes_datahub
from routes.routes_healthcentre import routes_healthcentre
from exception_handler import NotFoundException

app.register_blueprint(routes_admin)
app.register_blueprint(routes_encounter)
app.register_blueprint(routes_recording)
app.register_blueprint(routes_selection)
app.register_blueprint(routes_contour)
app.register_blueprint(routes_auth)
app.register_blueprint(routes_datahub)
app.register_blueprint(routes_healthcentre)

@app.errorhandler(OperationalError)
def handle_operational_error(e):
    print(e)
    # Redirect the user to a custom error page
    return redirect(url_for('operational_error'))

@app.route('/operational-error', endpoint='operational_error')
def operational_error():
    return render_template('operational-error.html')

# 404 Error Handler
@app.errorhandler(404)
def page_not_found(e):
    return "Page not found. Please check the URL and try again.", 404

# 405 Error Handler
@app.errorhandler(405)
def method_not_allowed(e):
    return "Method not allowed. Please check the request method and try again.", 405

# 500 Error Handler
@app.errorhandler(500)
def internal_server_error(e):
    return "Internal server error. Please try again later.", 500

# 502 Error Handler
@app.errorhandler(502)
def bad_gateway(e):
    return "Bad gateway. Please try again later.", 502

# 503 Error Handler
@app.errorhandler(503)
def service_unavailable(e):
    return "Service unavailable. Please try again later.", 503

# 504 Error Handler
@app.errorhandler(504)
def gateway_timeout(e):
    return "Gateway timeout. Please try again later.", 504

@app.errorhandler(NotFoundException)
def not_found(e):
    return render_template('error.html', error_code=404, error_message='This page does not exist.', goback_link='/home', goback_message="Home")

# Generic Error Handler
# @app.errorhandler(Exception)
# def generic_error_handler(e):
#     return "An error occurred that could not be automatically resolved. Please contact your system administrator with instructions to reproduce it and try again later.", 500

@app.route('/favicon.ico')
def favicon():
    """For the Web App's favicon"""
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route('/image/<path:path>')
def get_image(path):
    # Path to the PNG file
    image_path = path

    # Return the PNG file as a response
    return send_file(image_path, mimetype='image/png')


@app.before_request
def before_request():
    """
    Before each webapp request this function will be called. It will store user information in the `g` object
    which can then be accessed by the HTML templates.
    """
    g.user = current_user


@app.route('/enter-snapshot-date-in-session', methods=['GET'])
def enter_snapshot_date_in_session():
    """
    Enter the snapshot date into the session. This works well
    to enter the snapshot date into the session so that it can be
    passed to new requests.
    """
    snapshot_date = request.args.get('archive-mode-date')
    redirect_link = request.args.get('redirect-link')
    client_session['snapshot_date'] = snapshot_date
    print(client_session['snapshot_date'])
    return redirect(redirect_link)

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

@app.route('/reset-snapshot-in-session-with-link', methods=['GET','POST'])
def reset_snapshot_in_session_with_link():
    """
    Remove the snapshot date from the session, therefore exiting out of archive mode. 
    After the snapshot date has been removed, redirect the user to a link provided
    in a form element with the POST request submission, redirect_link.
    """
    redirect_link = request.form.get('redirect_link')
    client_session['snapshot_date'] = None
    return redirect(remove_snapshot_date_from_url(redirect_link))

@app.route('/reset-snapshot-in-session', methods=['GET','POST'])
def reset_snapshot_in_session():
    """
    Remove the snapshot date from the session, therefore exiting out of archive mode.
    Once complete redirect the user back to the page that they were on.
    """
    client_session['snapshot_date']=None
    return redirect(remove_snapshot_date_from_url(request.referrer))

@app.route('/resources/<path:filename>')
def serve_resource(filename):
    """
    Serve a file from the 'resources' directory (for resources such as images).
    """
    return send_from_directory('resources', filename)

@app.route('/static/js/<path:filename>')
def serve_script(filename):
    """
    Serve a file from the 'static/js' directory (for JS).
    """
    return send_from_directory('static/js', filename)

@app.route('/static/css/<path:filename>')
def serve_style(filename):
    """
    Serve a file from the 'static/css' directory (for CSS).
    """
    return send_from_directory('static/css', filename)

# def get_file_path(relative_path):
#     if relative_path != "":
#         return os.path.join(FILE_SPACE_PATH,relative_path)
#     else:
#         return None

# TODO: download folder should no longer be used. Rather a bulk download should
# collect various individual files and zip them together (not an entire folder)
@app.route('/download-folder/<path:relative_path>')
def download_folder(relative_path):
    """
    DEPRACATED
    Download files from a specified folder and send them as a zip file for download.
    """
    if relative_path != "":
        folder_path = os.path.join(FILE_SPACE_PATH, relative_path)
        zip_path = os.path.join(FILE_SPACE_PATH, f"{relative_path}.zip")

        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    zipf.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), folder_path))

        # Send the zip file for download
        response = send_file(zip_path, as_attachment=True)

        # Delete the temporary zip file
        os.remove(zip_path)

        return response

@app.route('/download-file/<path:relative_path>')
def download_file(relative_path):
    """
    Download a file from the FILE_SPACE_PATH.
    """
    if relative_path != "":
        file_path = os.path.join(FILE_SPACE_PATH, relative_path)
        return send_file(file_path, as_attachment=True)

@app.route('/')
def hello_world():
    """
    Redirect user from root to home directory.
    """
    return redirect(url_for('home', user=current_user))

@app.route('/api/users')
def search_users():
    """
    API endpoint to search users based on the search term.
    """
    search_term = request.args.get('search')
    with Session() as session:
        users = session.query(User).filter(
            or_(
                User.name.ilike(f'%{search_term}%'),
                User.login_id.ilike(f'%{search_term}%')
            ),
            User.is_temporary == False
        ).all()
        user_list = [{'id': user.id, 'name': user.name, 'login_id': user.login_id} for user in users]
        return jsonify({'users': user_list})

@app.route('/home') 
@login_required
def home():
    """
    Route for the home page.
    """

    with Session() as session:
        result = session.query(Recording, Assignment). \
            join(Assignment, Assignment.recording_id == Recording.id). \
            filter(Assignment.user_id == current_user.id). \
            order_by((Recording.status == "On Hold").desc()). \
            order_by(Assignment.completed_flag). \
            order_by(Assignment.created_datetime.desc()). \
            all()

        

        recordings = [{'recording': recording, 'assignment': assignment} for recording, assignment in result]

        return render_template('home.html', user=current_user, recordings=recordings)

if __name__ == '__main__':
    app.run(debug=True)