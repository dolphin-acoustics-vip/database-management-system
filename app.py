import uuid
import MySQLdb
from flask import Flask, flash,get_flashed_messages, jsonify, redirect,render_template,request, send_file,session, url_for
from flask_mysqldb import MySQL
from flask import send_from_directory
from sqlalchemy.orm import joinedload
import sqlalchemy.exc

import pprint
import database
from sqlalchemy.orm import sessionmaker




from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from models import *

from db import db



import os

app = Flask(__name__)
app.secret_key = 'kdgnwinhuiohji3275y3hbhjex?1'

# Configure the database connection using SQLAlchemy and MariaDB
app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+mysqldb://{os.environ['STADOLPHINACOUSTICS_USER']}:{os.environ['STADOLPHINACOUSTICS_PASSWORD']}@{os.environ['STADOLPHINACOUSTICS_HOST']}/{os.environ['STADOLPHINACOUSTICS_DATABASE']}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

UPLOAD_FOLDER = 'uploads'

db.init_app(app)

# Create the engine and session within a route or a view function
with app.app_context():
    engine = db.get_engine()
    Session = sessionmaker(bind=engine)


@app.route('/')
def hello_world():
    return "Root Page"
@app.route('/home')
def home():
    return render_template('home.html')


@app.route('/species')
def view_species():
    session = Session()
    try:
        species_data = session.query(Species).all()
        return render_template('species.html', species_list=species_data)
    except Exception as e:
        raise e
    finally:
        session.close()

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

@app.route('/species/edit/<uuid:species_id>', methods=['GET', 'POST'])
def edit_species(species_id):
    try:
        session = Session()
        species_data = session.query(Species).filter_by(id=species_id).first()
        
        if request.method == 'POST':
            if species_data:
                species_name = request.form['species_name']
                genus_name = request.form['genus_name']
                common_name = request.form['common_name']

                species_data.set_species_name(species_name)
                species_data.set_genus_name(genus_name)
                species_data.set_common_name(common_name)
                
                session.commit()

                flash('Species updated: {}'.format(species_name), 'success')
                return redirect('/species')
            else:
                flash('Species with ID {} not found'.format(species_id), 'error')
                return redirect('/species')
        else:
            return render_template('edit_species.html', species=species_data)
    except Exception as e:
        session.rollback()
        flash(str(e), 'error')
        return redirect('/species')
    finally:
        session.close()
    

# Define a route to clear flashed messages
@app.route('/clear_flashed_messages', methods=['POST'])
def clear_flashed_messages():
    flashed_messages = get_flashed_messages(with_categories=True)  # Retrieve flashed messages
    for category, message in flashed_messages:
        session['_flashes'].remove((category, message))  # Remove specific flashed message from the session
        
    return jsonify({'message': 'Flashed messages cleared'})

# Update the route handler to use SQLAlchemy for deleting a species from the table
@app.route('/species/delete/<uuid:species_id>', methods=['POST', 'DELETE'])
def delete_species(species_id):
    
    if request.method == 'POST' or request.method == 'DELETE':
        try:
            species_name = database.get(Species, species_id).get_species_name()
            database.delete(Species,species_id)

            flash('Species deleted: {}'.format(species_name), 'success')
            return redirect('/species')
        except database.SQLError as e:
            flash(e.get_error_description(), 'error')
            return redirect('/species')

    else:
        flash('Failed to delete species {}'.format(species_id), 'error')
        return redirect('/species')
    
@app.route('/species/add', methods=['GET', 'POST'])
def add_species():
    if request.method == 'POST':
        species_name = request.form['species_name']
        genus_name = request.form['genus_name']
        common_name = request.form['common_name']
        
        session = Session()
        try:
            new_species = Species(species_name=species_name, genus_name=genus_name, common_name=common_name)
            session.add(new_species)
            
            session.commit()
            flash('Species added: {}.'.format(species_name), 'success')
            return redirect('/species')

        except database.SQLError as e:
            flash(e.get_error_description(), 'error')
            session.rollback()
            return redirect('/species')
        finally:
            session.close()
    return render_template('add_species.html')


@app.route('/encounter/add', methods=['GET', 'POST'])
def add_encounter():
    if request.method == 'POST':
        encounter_name = request.form['encounter_name']
        location = request.form['location']
        species_id = request.form['species']
        origin = request.form['origin']
        notes = request.form['notes']

        session = Session()
        try:
            new_encounter = Encounter()
            new_encounter.set_encounter_name(encounter_name)
            new_encounter.set_location(location)
            new_encounter.set_origin(origin)
            new_encounter.set_notes(notes)
            new_encounter.set_species_id(species_id)
            session.add(new_encounter)

            session.commit()
            flash(f'Encounter added: {encounter_name}', 'success')
            return redirect('/encounter')
        except database.SQLError as e:
            flash(e.get_error_description(), 'error')
            session.rollback()
            return redirect('/encounter')
        finally:
            session.close()
    else:
        session = Session()
        species_list = session.query(Species).all()
        session.close()
        return render_template('add_encounter.html', species_list=species_list)

@app.route('/encounter', methods=['GET'])
def encounter_details():
    session = Session()
    try:
        # Fetch encounter details from the database
        encounter_list = session.query(Encounter).join(Species).all()

        if len(encounter_list) < 1:
            species_data = session.query(Species).all()
            if len(species_data) < 1:
                return render_template('error.html', error_code=404, error_message='No encounter data found. You cannot add encounter data until there are species to add the encounter for.', goback_link='/home', goback_message="Home")

        return render_template('encounter.html', encounter_list=encounter_list)
    except Exception as e:
        raise e
    finally:
        session.close()

@app.route('/encounter/delete/<uuid:encounter_id>', methods=['GET', 'POST'])
def delete_encounter(encounter_id):
    session = Session()
    encounter = session.query(Encounter).filter_by(id=encounter_id).first()

    if request.method == 'POST':
        try:
            # Delete the encounter from the database
            session.delete(encounter)
            session.commit()
            flash(f'Encounter deleted: {encounter.get_encounter_name()}-{encounter.get_location()}.', 'success')
            return redirect('/encounter')
        except sqlalchemy.exc.SQLAlchemyError as e:
            flash(database.parse_alchemy_error(e), 'error')
            session.rollback()
            return redirect('/encounter')
        finally:
            session.close()
    else:
        return render_template('delete_encounter.html', encounter=encounter)

@app.route('/encounter/view/<uuid:encounter_id>', methods=['GET'])
def view_encounter(encounter_id):
    # Create a new session within the request context
    with Session() as session:
        # Query the Encounter object with the species relationship loaded
        encounter = session.query(Encounter).options(joinedload(Encounter.species)).filter_by(id=encounter_id).first()
        
        # Query the recordings related to the encounter
        recordings = session.query(Recording).filter(Recording.encounter_id == encounter_id).all()

        # No need to manually close the session due to the context manager

        return render_template('view_encounter.html', encounter=encounter, recordings=recordings)


@app.route('/encounter/view/<uuid:encounter_id>/add_recording', methods=['POST'])
def add_recording(encounter_id):
    session = Session()
    if request.method == 'POST':
        try:
            recording_obj = add_or_edit_recording(session, request, encounter_id)
            session.add(recording_obj)
            session.commit()
            flash(f'Added recording: {recording_obj.id}', 'success')
            return redirect(url_for('view_encounter', encounter_id=encounter_id))
        except database.SQLError as e:
            flash(e.get_error_description(), 'error')
            session.rollback()
            return redirect(url_for('view_encounter', encounter_id=encounter_id))
        finally:
            session.close()

def add_or_edit_recording(session, request, encounter_id, recording_id=None):
    encounter = session.query(Encounter).filter_by(id=encounter_id).first()
    root_path = UPLOAD_FOLDER

    time_start = request.form['time_start']
    seconds = request.form['seconds']

    if recording_id is not None:
        new_recording = session.query(Recording).filter_by(id=recording_id).first()
    else:
        new_recording = Recording()

    new_recording.set_start_time(time_start, seconds)
    new_recording.set_duration(0)
    new_recording.set_encounter_id(encounter_id)
    session.add(new_recording)
    session.commit()

    # Handle recording file
    if 'recording_file' in request.files and request.files['recording_file'].filename != '':
        recording_file = request.files['recording_file']

        new_recording_filename = new_recording.generate_recording_filename()
        new_relative_path = new_recording.generate_relative_path()
        new_file = File()
        new_file.insert_path_and_filename(recording_file, new_relative_path, new_recording_filename, root_path)
        new_file.set_uploaded_date = datetime.now()
        new_file.set_uploaded_by("User 1")
        session.add(new_file)

        new_recording.recording_file = new_file

    # Handle selection file
    if 'selection_file' in request.files and request.files['selection_file'].filename != '':
        selection_file = request.files['selection_file']

        new_selection_filename = new_recording.generate_selection_filename()
        new_relative_path = new_recording.generate_relative_path()
        new_file = File()
        new_file.insert_path_and_filename(selection_file, new_relative_path, new_selection_filename, root_path)
        new_file.set_uploaded_date = datetime.now()
        new_file.set_uploaded_by("User 1")
        session.add(new_file)

        new_recording.selection_file = new_file

    session.commit()

    return new_recording

@app.route('/encounter/view/<uuid:encounter_id>/edit_recording/<uuid:recording_id>', methods=['POST'])
def edit_recording(encounter_id, recording_id):
    if request.method=='POST':
        with Session() as session:
            try:
                recording_obj = add_or_edit_recording(session, request, encounter_id, recording_id)
                flash(f'Edited recording: {recording_obj.id}', 'success')                
                session.commit()
                return redirect(url_for('view_encounter', encounter_id=encounter_id))
            except database.SQLError as e:
                flash(e.get_error_description(), 'error')
                session.rollback()
                return redirect(url_for('view_encounter', encounter_id=encounter_id))
            finally:
                session.close()


@app.route('/encounter/view/<uuid:encounter_id>/delete-recording-file/<uuid:file_id>')
def delete_recording_file(encounter_id,file_id):
    with Session() as session:
        try:
            recording = session.query(Recording).filter_by(recording_file_id=file_id).first()
            recording.recording_file=None
            
            file = session.query(File).filter_by(id=file_id).first()
            try:
                file_path = file.get_full_relative_path()
                file.move_to_trash()
                session.delete(file)
                session.commit()
                flash(f'Deleted file: {file_path}', 'success')

            except FileNotFoundError:
                session.commit()
                flash(f'Deleted file record but could not find file: {file_path}', 'success')
            
            return redirect(url_for('view_encounter', encounter_id=encounter_id))
        except database.SQLError as e:
            flash(e.get_error_description(), 'error')
            session.rollback()
            return redirect(url_for('view_encounter', encounter_id=encounter_id))
        finally:
            session.close()

@app.route('/encounter/view/<uuid:encounter_id>/delete-selection-file/<uuid:file_id>')
def delete_selection_file(encounter_id,file_id):
    with Session() as session:
        try:
            recording = session.query(Recording).filter_by(selection_file_id=file_id).first()
            recording.selection_file=None
            
            file = session.query(File).filter_by(id=file_id).first()
            try:
                file_path = file.get_full_relative_path()
                file.move_to_trash()
                session.delete(file)
                session.commit()
                flash(f'Deleted file: {file_path}', 'success')

            except FileNotFoundError:
                session.commit()
                flash(f'Deleted file record but could not find file: {file_path}', 'success')
            
            return redirect(url_for('view_encounter', encounter_id=encounter_id))
        except database.SQLError as e:
            flash(e.get_error_description(), 'error')
            session.rollback()
            return redirect(url_for('view_encounter', encounter_id=encounter_id))
        finally:
            session.close()


@app.route('/download_folder/<path:path>')
def download_files_from_folder(path):
    import zipfile
    print("DOWNLOAD",path)

    if path!="":
        folder_path = os.path.join(UPLOAD_FOLDER, path)
        zip_path = os.path.join(UPLOAD_FOLDER, f"{path}.zip")
        
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    zipf.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), folder_path))

        return send_file(zip_path, as_attachment=True)

@app.route('/download_file/<path:full_path>')
def download_file_from_uploads(full_path):
    if full_path!="":
        
        # Assuming the files are stored in a directory named 'uploads'
        # You may need to adjust the file path based on your actual file storage setup
        file_path = os.path.join(UPLOAD_FOLDER, full_path)
        
        return send_file(file_path, as_attachment=True) 


@app.route('/encounter/edit/<uuid:encounter_id>', methods=['GET', 'POST'])
def edit_encounter(encounter_id):
    try:
        session = Session()
        encounter = session.query(Encounter).join(Species).filter(Encounter.id == encounter_id).first()
        species_list = session.query(Species).all()

        if request.method == 'POST':
            encounter.set_encounter_name(request.form['encounter_name'])
            encounter.set_location(request.form['location'])
            encounter.set_species_id(request.form['species'])
            encounter.set_origin(request.form['origin'])
            encounter.set_notes(request.form['notes'])
            encounter_updated(session, encounter_id)
            flash('Updated encounter: {}.'.format(encounter.encounter_name), 'success')
            return redirect('/encounter')

        return render_template('edit_encounter.html', encounter=encounter, species_list=species_list)

    except database.SQLError as e:
        raise e
        flash(e.get_error_description(), 'error')
        session.rollback()
        return redirect('/encounter')
    except Exception as e:
        raise e
        print("EXCEPTING")
        session.rollback()
        raise e
    finally:
        session.close()

if __name__ == '__main__':
    app.run(debug=True)