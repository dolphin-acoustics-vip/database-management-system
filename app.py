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
from db import Session, UPLOAD_FOLDER, GOOGLE_API_KEY, app
from models import *
from routes.routes_admin import routes_admin
from routes.routes_encounter import routes_encounter
from routes.routes_recording import routes_recording
from routes.routes_selection import routes_selection
from routes.routes_species import routes_species

app.register_blueprint(routes_admin)
app.register_blueprint(routes_species)
app.register_blueprint(routes_encounter)
app.register_blueprint(routes_recording)
app.register_blueprint(routes_selection)

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

@app.route('/download_folder/<path:path>')
def download_files_from_folder(path):
    print("DOWNLOAD", path)

    if path != "":
        folder_path = os.path.join(UPLOAD_FOLDER, path)
        print("folder path", folder_path)
        zip_path = os.path.join(UPLOAD_FOLDER, f"{path}.zip")
        print(zip_path)

        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for root, dirs, files in os.walk(folder_path):
                print(root, dirs, files)
                for file in files:
                    print(file)
                    zipf.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), folder_path))

        # Send the zip file for download
        response = send_file(zip_path, as_attachment=True)

        # Delete the temporary zip file
        os.remove(zip_path)

        return response

@app.route('/download_file/<path:full_path>')
def download_file_from_uploads(full_path):
    if full_path!="":
        
        # Assuming the files are stored in a directory named 'uploads'
        # You may need to adjust the file path based on your actual file storage setup
        file_path = os.path.join(UPLOAD_FOLDER, full_path)
        
        return send_file(file_path, as_attachment=True) 



if __name__ == '__main__':
    app.run(debug=True)