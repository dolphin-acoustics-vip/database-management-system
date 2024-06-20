# Standard library imports
import pandas as pd
import uuid, os, re
import shared_functions

# Third-party imports
from flask import Blueprint, flash,get_flashed_messages, jsonify, redirect,render_template,request, send_file, url_for, send_from_directory
from flask import session as client_session
from sqlalchemy.exc import SQLAlchemyError
from flask_login import login_user,login_required, current_user, login_manager

# Local application imports
from db import FILE_SPACE_PATH, Session, GOOGLE_API_KEY, parse_alchemy_error, save_snapshot_date_to_session, get_snapshot_date_from_session,require_live_session,exclude_role_1,exclude_role_2,exclude_role_3,exclude_role_4

from models import *
from exception_handler import *

routes_recording = Blueprint('recording', __name__)


def insert_or_update_recording(session, request, encounter_id, recording_id=None):
    """
    Insert or update a recording in the database. This function should be called
    by routes either inserting (new) Recording objects or updating (existing) 
    Recording objects.

    Parameters:
    - session: the database session (which will be used to insert or update)
    - request: the HTTP request object (containing the insert or update form)
    - encounter_id: the ID of the encounter the recording belongs to
    - recording_id: (optional) the ID of the recording to update, or None to insert

    Returns:
    - new_recording: the newly inserted or updated recording
    """
    
    time_start = request.form['time_start']
    # Get Recording object if updating or make a new one is inserting.
    # This is decided by whether recording_id is None or not.
    if recording_id is not None:
        new_recording = session.query(Recording).filter_by(id=recording_id).first()
    else:
        new_recording = Recording()

    
    seconds = request.form['seconds']
    new_recording.set_start_time(time_start, seconds)
    new_recording.set_duration(0)
    new_recording.set_encounter_id(encounter_id)
    new_recording.set_user_id(current_user.id)
    session.add(new_recording)
    session.commit()

    # If a recording file has been given, add it to the Recording object
    if 'recording_file' in request.files and request.files['recording_file'].filename != '':
        recording_file = request.files['recording_file']
        new_recording_filename = new_recording.generate_recording_filename()
        new_relative_path = new_recording.generate_relative_path()
        new_file = File()
        new_file.insert_path_and_filename(recording_file, new_relative_path, new_recording_filename, FILE_SPACE_PATH)
        new_file.set_uploaded_date = datetime.now()
        new_file.set_uploaded_by("User 1")
        session.add(new_file)
        new_recording.recording_file = new_file
    
    # If a selection file has been given, add it to the Recording object
    if 'selection_table_file' in request.files and request.files['selection_table_file'].filename != '':
        selection_table_file = request.files['selection_table_file']
        new_selection_table_filename = new_recording.generate_selection_table_filename()
        new_relative_path = new_recording.generate_relative_path()
        new_file = File()
        new_file.insert_path_and_filename(selection_table_file, new_relative_path, new_selection_table_filename, FILE_SPACE_PATH)
        new_file.set_uploaded_date = datetime.now()
        new_file.set_uploaded_by("User 1")
        session.add(new_file)
        new_recording.reset_all_selections_unresolved_warnings(session)
        new_recording.selection_table_file = new_file    
    session.commit()
    return new_recording




@routes_recording.route('/encounter/<uuid:encounter_id>/recording/<uuid:recording_id>/selection-table/add', methods=['POST'])
@require_live_session
def recording_selection_table_add(encounter_id,recording_id):
    """
    Given a selection table file in the POST request (selection-table-file), add it to the recording
    after validation. 
    """
    with Session() as session:
        recording = session.query(Recording).filter_by(id=recording_id).first()
        # If a selection file has been given, add it to the Recording object
        if 'selection-table-file' in request.files and request.files['selection-table-file'].filename != '':
            selection_table_file = request.files['selection-table-file'] # required in the POST request
            # Generate the destination filename and filepath for the selection table
            new_selection_table_filename = recording.generate_selection_table_filename()
            new_relative_path = recording.generate_relative_path()
            new_file = File()
            new_file.insert_path_and_filename(selection_table_file, new_relative_path, new_selection_table_filename, FILE_SPACE_PATH)
            new_file.set_uploaded_date = datetime.now()
            new_file.set_uploaded_by("User 1") # TODO: change
            session.add(new_file)
            recording.selection_table_file = new_file 
            # Validate the selection table - if invalid then delete the selection table file
            error_msg = recording.validate_selection_table(session)
            if error_msg != None and error_msg != "":
                new_file.move_to_trash(session)
                handle_exception(error_msg, session)
                return redirect(url_for('recording.recording_view', encounter_id=encounter_id, recording_id=recording_id))
        session.commit()  
    
    return redirect(url_for('recording.recording_view', encounter_id=encounter_id, recording_id=recording_id))
 
@routes_recording.route('/encounter/<uuid:encounter_id>/recording/<uuid:recording_id>/selection-table/delete', methods=['POST'])
@require_live_session
def recording_selection_table_delete(encounter_id, recording_id):
    """
    Delete the selection table file associated with the recording
    """
    with Session() as session:
        try:
            print("I GOT HERE")
            recording = session.query(Recording).filter_by(id=recording_id).first()
            recording.selection_table_file=None
            file = session.query(File).filter_by(id=recording.selection_table_file_id).first()
            try:
                print("TRYING",recording,recording.selection_table_file)
                # All manually resolved warnings will be reset to 'unresolved' (forcing
                # them to be re-validated after the selection table is deleted)
                session.commit()
                flash(f'Deleted Selection Table', 'success')
                file.move_to_trash()
            except FileNotFoundError:
                print("ERROR")
                session.commit()
                flash(f'Deleted Selection Table', 'success')
        except SQLAlchemyError as e:
            handle_sqlalchemy_exception(session, e)
        finally:
            return redirect(url_for('recording.recording_view', encounter_id=encounter_id, recording_id=recording_id))

@routes_recording.route('/encounter/<uuid:encounter_id>/recording/insert', methods=['POST'])
@require_live_session
def recording_insert(encounter_id):
    """
    Inserts a new recording into the database for a given encounter ID.
    """
    with Session() as session:
        try:
            recording_obj = insert_or_update_recording(session, request, encounter_id)
            session.add(recording_obj)
            session.commit()
            flash(f'Added recording: {recording_obj.id}', 'success')
            return redirect(url_for('encounter.encounter_view', encounter_id=encounter_id))
        except SQLAlchemyError as e:
            raise e
            flash(parse_alchemy_error(e), 'error')
            session.rollback()
            return redirect(url_for('encounter.encounter_view', encounter_id=encounter_id))

@routes_recording.route('/recording/<uuid:recording_id>/get-unresolved-warnings', methods=['GET'])
def get_number_of_unresolved_warnings(recording_id):
    with Session() as session:
        recording = shared_functions.create_system_time_request(session, Recording, {"id":recording_id})

        # Prepare the response data
        response_data = {
            'recording_id': recording_id,
            'number_of_unresolved_warnings': recording.get_number_of_unresolved_warnings()
        }
        return jsonify(response_data)
    
    

@routes_recording.route('/encounter/<uuid:encounter_id>/recording/<uuid:recording_id>/view', methods=['GET'])
def recording_view(encounter_id,recording_id):
    """
    Renders the recording view page for a specific encounter and recording.
    """
    
    if request.args.get('snapshot_date'):
        save_snapshot_date_to_session(request.args.get('snapshot_date'))

    with Session() as session:
        
        recording = shared_functions.create_system_time_request(session, Recording, {"id":recording_id})[0]
        

        #recording = query.filter_by(id=recording_id).first()
        selections = shared_functions.create_system_time_request(session, Selection, {"recording_id":recording_id}, order_by="selection_number")

        
        #recording_audit = session.query(RecordingAudit).filter_by(record_id=recording.id).all()
        from sqlalchemy.sql import select
        # Retrieve the historical records of a row
        
        #sql_query = session.query(Recording).filter_by(id=recording_id).all()

        recording_history = shared_functions.create_all_time_request(session, Recording, filters={"id":recording_id}, order_by="row_start")
        
        return render_template('recording/recording-view.html', recording=recording, selections=selections, user=current_user,recording_history=recording_history)

@routes_recording.route('/encounter/<uuid:encounter_id>/recording/<uuid:recording_id>/update', methods=['POST'])
@require_live_session
def recording_update(encounter_id, recording_id):
    """
    Updates a recording in the encounter with the specified encounter ID and recording ID.
    """
    with Session() as session:
        try:
            recording_obj = insert_or_update_recording(session, request, encounter_id, recording_id)
            recording_obj.update_call(session)
            session.commit()
            flash(f'Edited recording: {recording_obj.id}', 'success')                
            return redirect(url_for('encounter.encounter_view', encounter_id=encounter_id))
        except SQLAlchemyError as e:
            flash(parse_alchemy_error(e), 'error')
            session.rollback()
            return redirect(url_for('encounter.encounter_view', encounter_id=encounter_id))

@routes_recording.route('/encounter/<uuid:encounter_id>/recording/<uuid:recording_id>/delete', methods=['GET'])
@require_live_session
def recording_delete(encounter_id,recording_id):
    """
    Function for deleting a recording of a given ID
    """
    with Session() as session:
        try:
            recording = session.query(Recording).filter_by(id=recording_id).first()
            recording.delete(session)
            session.commit()
            flash(f'Deleted recording: {recording.id}', 'success')
            return redirect(url_for('encounter.encounter_view', encounter_id=encounter_id))
        except SQLAlchemyError as e:
            flash(parse_alchemy_error(e), 'error')
            session.rollback()
            return redirect(url_for('encounter.encounter_view', encounter_id=encounter_id))

@routes_recording.route('/encounter/<uuid:encounter_id>/recording/<uuid:recording_id>/recording-file/<uuid:file_id>/delete',methods=['GET'])
@require_live_session
def recording_file_delete(encounter_id,recording_id,file_id):
    """
    A function for deleting a recording file of a given ID
    """
    with Session() as session:
        try:
            recording = session.query(Recording).filter_by(recording_file_id=file_id).first()
            # Remove recording file reference from recording
            recording.recording_file=None
            # Delete the File object for the recording file its self
            file = session.query(File).filter_by(id=file_id).first()
            file_path = file.get_full_relative_path()
            try:
                file.delete(session)
                session.commit()
                flash(f'Deleted file: {file_path}', 'success')
            except FileNotFoundError:
                session.commit()
                flash(f'Deleted file record but could not find file: {file_path}', 'success')
            return redirect(url_for('encounter.encounter_view', encounter_id=encounter_id))
        except SQLAlchemyError as e:
            flash(parse_alchemy_error(e), 'error')
            session.rollback()
            return redirect(url_for('encounter.encounter_view', encounter_id=encounter_id))

@routes_recording.route('/recording/<uuid:recording_id>/recording_delete_selections', methods=['DELETE'])
@require_live_session
def recording_delete_selections(recording_id):
    if request.method == 'DELETE':
        data = request.get_json()
        selection_ids = data.get('selectionIds', [])
        
        session = Session()
        try:
            counter=0
            for selection_id in selection_ids:
                selection_id = uuid.UUID(selection_id)  # Convert the string to a UUID object

                selection = session.query(Selection).filter_by(id=selection_id).first()
                selection_number = selection.selection_number
                selection.delete(session)
                counter += 1
            flash(f'Deleted {counter} selections', 'success')

            session.commit()
            return jsonify({'message': 'Bulk delete completed'}), 200
        except SQLAlchemyError as e:
            session.rollback()
            flash(parse_alchemy_error(e), 'error')
            return jsonify({'error': parse_alchemy_error(e)}), 500
        finally:
            session.close()
    else:
        return jsonify({'error': 'Method not allowed'}), 405


@routes_recording.route('/recording/recording_selection_table_ignore_warnings/<uuid:recording_id>', methods=['POST'])
@require_live_session
def recording_selection_table_ignore_warnings(recording_id):
    session = Session()
    data = request.get_json()
    try:
        recording = session.query(Recording).filter_by(id=recording_id).first()
        recording.ignore_selection_table_warnings = not recording.ignore_selection_table_warnings
        session.commit()
        return jsonify({'ignore_selection_table_warnings': recording.ignore_selection_table_warnings}), 200
    except SQLAlchemyError as e:
        session.rollback()
        flash(parse_alchemy_error(e), 'error')
        return jsonify({'error': parse_alchemy_error(e)}), 500
    finally:
        session.close()


@routes_recording.route('/encounter/<uuid:encounter_id>/recording/<uuid:recording_id>/check-selection-table', methods=['GET'])
def check_selection_table(encounter_id, recording_id):
    return_string = "None"
    
    with Session() as session:
        try:
            recording = session.query(Recording).filter_by(id=recording_id).first()
            selections = session.query(Selection).filter_by(recording_id=recording_id).all()
            selection_numbers = []
            for selection in selections:
                selection_numbers.append(selection.selection_number)
                
            selection_table_file = recording.selection_table_file
            if selection_table_file == None:
                raise FileNotFoundError()   
            else:
                selection_table_file_path = selection_table_file.get_full_absolute_path()
                if os.path.exists(selection_table_file_path):
                    # parse CSV file and check if the selection numbers exist in 
                    # the list above selection_numbers
                    pass
        except Exception as e:
            return(str(e))
        
        return return_string

  

@routes_recording.route('/encounter/extract_date', methods=['GET'])
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
