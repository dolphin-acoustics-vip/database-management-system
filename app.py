import re, uuid, zipfile, os
from flask import Flask, flash,get_flashed_messages, jsonify, redirect,render_template,request, send_file,session, url_for, send_from_directory
from sqlalchemy.orm import joinedload,sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from db import app,Session,UPLOAD_FOLDER,GOOGLE_API_KEY
import db
from models import *
from routes.routes_admin import routes_admin
from routes.routes_species import routes_species
from routes.routes_encounter import routes_encounter
from routes.routes_recording import routes_recording
from routes.routes_selection import routes_selection

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
# test


@app.route('/')
def hello_world():
    return "Root Page"
@app.route('/home')
def home():
    return render_template('home.html')



# Route to serve the image file from the resources directory
@app.route('/resources/<path:filename>')
def download_file(filename):
    return send_from_directory('resources', filename)


# Add a route to serve the general-style.css file
@app.route('/static/css/general-style.css')
def serve_general_style():
    return send_from_directory('static/css', 'general-style.css')

# Add a route to serve the hero-section.css file
@app.route('/static/css/hero-section.css')
def serve_hero_section():
    return send_from_directory('static/css', 'hero-section.css')


# Define a route to clear flashed messages
@app.route('/clear_flashed_messages', methods=['POST'])
def clear_flashed_messages():
    flashed_messages = get_flashed_messages(with_categories=True)  # Retrieve flashed messages
    for category, message in flashed_messages:
        session['_flashes'].remove((category, message))  # Remove specific flashed message from the session
        
    return jsonify({'message': 'Flashed messages cleared'})

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