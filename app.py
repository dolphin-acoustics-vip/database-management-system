# Standard library imports
import os
import zipfile

# Third-party imports
from flask import (Flask, flash, get_flashed_messages, jsonify, redirect,
                   render_template, request, send_file, session, url_for,
                   send_from_directory)
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload, sessionmaker

# Local application imports
from db import Session, FILE_SPACE_PATH, GOOGLE_API_KEY, app
from models import *
from routes.routes_admin import routes_admin
from routes.routes_encounter import routes_encounter
from routes.routes_recording import routes_recording
from routes.routes_selection import routes_selection
from routes.routes_contour import routes_contour

app.register_blueprint(routes_admin)
app.register_blueprint(routes_encounter)
app.register_blueprint(routes_recording)
app.register_blueprint(routes_selection)
app.register_blueprint(routes_contour)

'''
NOTE: to restrict access to certain routes, add the following to the routes.py file:
https://stackoverflow.com/questions/67806765/how-can-i-make-specific-routes-accessible-only-for-specific-users-in-flask 

from flask_login import current_user
# use the suggested pattern to login user then..

@users.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    if not current_user.is_admin:
        abort(403)
    # rest of your route

'''

@app.route('/resources/<path:filename>')
def serve_resource(filename):
    """
    Serve a file from the 'resources' directory (for resources such as images).
    """
    return send_from_directory('resources', filename)

@app.route('/static/css/<path:filename>')
def serve_style(filename):
    """
    Serve a file from the 'static/css' directory (for CSS).
    """
    return send_from_directory('static/css', filename)

def get_file_path(relative_path):
    if relative_path != "":
        return os.path.join(FILE_SPACE_PATH,relative_path)
    else:
        return None

@app.route('/download-folder/<path:relative_path>')
def download_folder(relative_path):
    """
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
    Download a file from the 'uploads' directory and send it for download.
    """
    if relative_path != "":
        file_path = os.path.join(FILE_SPACE_PATH, relative_path)
        return send_file(file_path, as_attachment=True)

@app.route('/')
def hello_world():
    """
    Redirect user from root to home directory.
    """
    return redirect(url_for('home'))

@app.route('/home')
def home():
    """
    Route for the home page.
    """
    return render_template('home.html')

if __name__ == '__main__':
    app.run(debug=True)