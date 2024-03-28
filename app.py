import re, uuid, zipfile, os
from flask import Flask, flash,get_flashed_messages, jsonify, redirect,render_template,request, send_file,session, url_for, send_from_directory
from sqlalchemy.orm import joinedload,sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from db import app,Session,UPLOAD_FOLDER,GOOGLE_API_KEY
import db
from models import *
from routes_admin import routes_admin
from routes_species import routes_species
from routes_encounter import routes_encounter

app.register_blueprint(routes_admin)
app.register_blueprint(routes_species)
app.register_blueprint(routes_encounter)

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
        except SQLAlchemyError as e:
            flash(db.parse_alchemy_error(e), 'error')
            session.rollback()
            return redirect(url_for('view_encounter', encounter_id=encounter_id))
        finally:
            session.close()


def add_or_edit_selection(session, selection_number, file, recording_id, selection_id=None):
    recording = session.query(Recording).filter_by(id=recording_id).first()


    if selection_id is not None:
        selection_obj = session.query(Selection).filter_by(id=selection_id).first()
    else:
        selection_obj = Selection()
    selection_obj.recording = recording
    session.add(selection_obj)
    
    selection_obj.set_selection_number(selection_number)

    # Handle recording file

    selection_file = file

    selection_filename = selection_obj.generate_filename()

    selection_relative_path = selection_obj.generate_relative_path()
    new_file = File()
    try:
        new_file.insert_path_and_filename(selection_file, selection_relative_path, selection_filename, UPLOAD_FOLDER)
    except IOError as e:
        if "File already exists" in str(e):
            if session.query(Selection).filter_by(selection_number=selection_number).filter_by(recording_id=recording_id).first() is not None:
                raise IOError (f"Selection selection {selection_number} for this recording already exists in the database.")
            else:
                raise IOError (f"A file with selection {selection_number} for this recording already exists. Cannot overwrite file. Please choose a different selection number or contact administrator to remove the file manually.")
        raise e
    new_file.set_uploaded_date(datetime.now())
    new_file.set_uploaded_by("User 1")

    selection_obj.selection_file = new_file
    selection_obj.selection_file_id = new_file.id

    session.add(new_file)

    return selection_obj


@app.route('/recording/view/<uuid:recording_id>', methods=['GET'])
def view_recording(recording_id):
    with Session() as session:
        recording = session.query(Recording).filter_by(id=recording_id).first()
        selections = session.query(Selection).filter_by(recording_id=recording_id).order_by(Selection.selection_number).all()
        return render_template('view_recording.html', recording=recording, selections=selections)

@app.route('/recording/view/<uuid:recording_id>/delete_selection/<uuid:selection_id>',methods=['DELETE'])
def delete_selection(recording_id, selection_id):
    session = Session()
    try:
        selection = session.query(Selection).filter_by(id=selection_id).first()
        selection_number = selection.selection_number
        selection.delete(session)

        session.commit()
        flash(f'Deleted selection: {selection_number}', 'success')
        return redirect(url_for('view_recording', recording_id=recording_id)),500
    except SQLAlchemyError as e:
        flash(db.parse_alchemy_error(e), 'error')
        session.rollback()
        return redirect(url_for('view_recording', recording_id=recording_id))
    finally:
        session.close()

@app.route('/recording/view/<uuid:recording_id>/bulk_delete_selections', methods=['DELETE'])
def bulk_delete_selections(recording_id):
    if request.method == 'DELETE':
        data = request.get_json()
        selection_ids = data.get('selectionIds', [])
        
        session = Session()
        try:
            for selection_id in selection_ids:
                selection_id = uuid.UUID(selection_id)  # Convert the string to a UUID object

                selection = session.query(Selection).filter_by(id=selection_id).first()
                selection_number = selection.selection_number
                selection.delete(session)
                flash(f'Deleted selection: {selection_number}', 'success')

            session.commit()
            return jsonify({'message': 'Bulk delete completed'}), 200
        except SQLAlchemyError as e:
            session.rollback()
            flash(db.parse_alchemy_error(e), 'error')
            return jsonify({'error': db.parse_alchemy_error(e)}), 500
        finally:
            session.close()
    else:
        return jsonify({'error': 'Method not allowed'}), 405

def process_uploaded_files(files):
    file_validity_info = []
    
    for file in files:
        file_name = file.filename
        is_valid = bool(re.match(r'sel_\d', file_name))
        file_validity_info.append({'file_name': file_name, 'is_valid': is_valid})
    
    return file_validity_info


@app.route('/update_selection_number', methods=['GET'])
def update_selection_number():
    messages = ""
    recording_id = str(request.args.get('recording_id'))
    print("RECORDING ID",recording_id)
    filename = request.args.get('filename')
    selection_number = request.args.get('selection_number')

    # Check if the selection number can be converted to an integer
    try:
        selection_number = int(selection_number)
    except ValueError:
        selection_number = None

    with Session() as session:
        
        recording = session.query(Recording).filter(db.text("id = :recording_id")).params(recording_id=recording_id).first()
        
        match = re.search(r'(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})', filename)
        if match:
            year = match.group(1)
            month = match.group(2)
            day = match.group(3)
            hour = match.group(4)
            minute = match.group(5)
            second = match.group(6)
            
            date_string = f"{day}/{month}/{year} {hour}:{minute}:{second}"
            date = datetime.strptime(date_string, '%d/%m/%Y %H:%M:%S')
            if not recording.match_start_time(date):
                messages += "Warning: start time in filename does not match. "

        else:
            messages += "Warning: no start time found in filename"


    # Add your logic here to update the selection number for the given filename
    # This could involve updating a database, writing to a file, or any other data storage method

    # For demonstration purposes, let's return the updated selection number in the response
    return jsonify(selection_number=selection_number, messages=messages)


@app.route('/extract_date', methods=['GET'])
def extract_date():
    filename = request.args.get('filename')
    date = None
    match = re.search(r'(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})', filename)
    if match:
        year = match.group(1)
        month = match.group(2)
        day = match.group(3)
        hour = match.group(4)
        minute = match.group(5)
        second = match.group(6)
        
        date_string = f"{day}/{month}/{year} {hour}:{minute}:{second}"
        date = datetime.strptime(date_string, '%d/%m/%Y %H:%M:%S')
    return jsonify(date=date)


@app.route('/extract_selection_number', methods=['GET'])
def extract_selection_number():
    recording_id = request.args.get('recording_id')
    filename = request.args.get('filename')
    selection_number = request.args.get('selection_number')
    valid = True
    messages=[]

    if selection_number == None or str(selection_number).strip() == "":
        selection_number = None


    
    # Extract the selection number from the filename using regular expression
    match = re.search(r'sel_(\d+)', filename)
    if match:
        if selection_number == None:
            selection_number = match.group(1).lstrip('0')  # Remove leading zeros
            messages.append("Selection number: " + selection_number + ".")
        else:
            if selection_number == match.group(1).lstrip('0'):
                messages.append("Selection number: " + selection_number + ".")
            else:
                messages.append("Warning: selection number mismatch.")
    elif not match and selection_number == None:
        messages.append("<span style='color: red;'>Error: invalid selection number.</span>")
        valid=False
    else:
        messages.append("Selection number: " + selection_number + ".")
    



    with Session() as session:

        if selection_number != None:
            selection_number_exits = session.query(Selection).filter(db.text("selection_number = :selection_number and recording_id = :recording_id")).params(selection_number=selection_number, recording_id=recording_id).first()
            if selection_number_exits:
                messages.append("<span style='color: red;'>Error: selection number already exists.</span>")
                valid=False

        recording = session.query(Recording).filter(db.text("id = :recording_id")).params(recording_id=recording_id).first()
        
        match = re.search(r'(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})', filename)
        if match:
            year = match.group(1)
            month = match.group(2)
            day = match.group(3)
            hour = match.group(4)
            minute = match.group(5)
            second = match.group(6)
            
            date_string = f"{day}/{month}/{year} {hour}:{minute}:{second}"
            date = datetime.strptime(date_string, '%d/%m/%Y %H:%M:%S')
            if not recording.match_start_time(date):
                messages.append("Warning: start time mismatch.")

        else:
            messages.append("Warning: no start time.")
    
    if selection_number != None and selection_number != "":
        try:
            int(selection_number)
        except Exception:
            messages.append("<span style='color: red;'>Error: invalid selection number.</span>")
            valid=False

    return jsonify(selection_number=selection_number,messages=messages,valid=valid)


@app.route('/recording/view/<uuid:recording_id>/review_files', methods=['GET', 'POST'])
def review_files(recording_id):
    try:
        with Session() as session:
            if 'selection_files' not in request.files:
                return jsonify({'error': 'No files found'}), 400

            # Access the uploaded files
            files = request.files.getlist('selection_files')
            selection_numbers = [request.form.get(f'selection_numbers[{i}]') for i in range(len(files ))]

            print(files)
            print(selection_numbers)
            # Process the files
            for i, file in enumerate(files):
                try:


                    add_or_edit_selection(session,selection_numbers[i], file, recording_id)
                    session.commit()
                    flash(f'Added selection {selection_numbers[i]}', 'success')
                except SQLAlchemyError as e:
                    session.rollback()
                    flash(db.parse_alchemy_error(e), 'error')
                except IOError as e:
                    session.rollback()
                    flash(str(e), 'error')
            session.commit()
            return jsonify({'message': 'Files uploaded successfully'}), 200
    except SQLAlchemyError as e:
        flash(db.parse_alchemy_error(e), 'error')
        return jsonify({'error': str(e)}), 500
    except IOError as e:
        flash(str(e), 'error')
        return jsonify({'error': str(e)}), 500
    


@app.route('/recording/view/<uuid:recording_id>/add_selection', methods=['POST'])
def add_selection(recording_id):
    session = Session()
    if request.method == 'POST':
        try:
            # Here you can save the uploaded selection file to a specific directory if needed
            # selection_file.save('path_to_save_directory/selection_filename')
            add_or_edit_selection(session, request.form['selection_number'], request.files['selection_file'], recording_id)
            session.commit()
            flash(f'Added selection for recording: {recording_id}', 'success')
            return redirect(url_for('view_recording', recording_id=recording_id))
        except SQLAlchemyError as e:
            flash(db.parse_alchemy_error(e), 'error')
            session.rollback()
            return redirect(url_for('view_recording', recording_id=recording_id))
        except IOError as e:
            flash(str(e), 'error')
            session.rollback()
            return redirect(url_for('view_recording', recording_id=recording_id))
            
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
                recording_obj.update_call(session)

                session.commit()
                clean_up_root_directory(os.path.join(ROOT_PATH,recording_obj.generate_relative_path()))
                flash(f'Edited recording: {recording_obj.id}', 'success')                
                return redirect(url_for('view_encounter', encounter_id=encounter_id))
            except SQLAlchemyError as e:
                flash(db.parse_alchemy_error(e), 'error')
                session.rollback()
                return redirect(url_for('view_encounter', encounter_id=encounter_id))
            finally:
                session.close()

@app.route('/encounter/view/<uuid:encounter_id>/delete-recording/<uuid:recording_id>')
def delete_recording(encounter_id,recording_id):
    with Session() as session:
        try:
            recording = session.query(Recording).filter_by(id=recording_id).first()
            recording.delete(session)
            session.commit()
            flash(f'Deleted recording: {recording.id}', 'success')
            return redirect(url_for('view_encounter', encounter_id=encounter_id))
        except SQLAlchemyError as e:
            flash(db.parse_alchemy_error(e), 'error')
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
            file_path = file.get_full_relative_path()
            try:
                file.delete(session)
                session.commit()
                flash(f'Deleted file: {file_path}', 'success')

            except FileNotFoundError:
                session.commit()
                flash(f'Deleted file record but could not find file: {file_path}', 'success')
            
            return redirect(url_for('view_encounter', encounter_id=encounter_id))
        except SQLAlchemyError as e:
            flash(db.parse_alchemy_error(e), 'error')
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
        except SQLAlchemyError as e:
            flash(db.parse_alchemy_error(e), 'error')
            session.rollback()
            return redirect(url_for('view_encounter', encounter_id=encounter_id))
        finally:
            session.close()


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