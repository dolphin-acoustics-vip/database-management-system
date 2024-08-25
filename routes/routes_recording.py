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
from db import get_file_space_path, Session, GOOGLE_API_KEY, parse_alchemy_error, save_snapshot_date_to_session, get_snapshot_date_from_session,require_live_session,exclude_role_1,exclude_role_2,exclude_role_3,exclude_role_4

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


    
    new_recording.set_start_time(time_start)
    new_recording.set_duration(0)
    new_recording.set_encounter_id(encounter_id)
    new_recording.set_user_id(current_user.id)
    session.add(new_recording)
    session.flush()

    # If a recording file has been given, add it to the Recording object
    if 'recording_file' in request.files and request.files['recording_file'].filename != '':
        recording_file = request.files['recording_file']
        new_recording_filename = new_recording.generate_recording_filename()
        new_relative_path = new_recording.generate_relative_path()
        new_file = File()
        session.add(new_file)
        new_recording.recording_file = new_file
        new_file.insert_path_and_filename(session, recording_file, new_relative_path, new_recording_filename, get_file_space_path())
        session.commit()
        
    
    if 'assign_user_id' in request.form:
        assign_user_id = request.form['assign_user_id'] 
        try:
            user_id_uuid = uuid.UUID(assign_user_id)
            user_obj = session.query(User).filter_by(id=user_id_uuid).first()

        except ValueError:
            user_obj=None
        if user_obj is not None:
            assignment = Assignment()
            assignment.recording_id = new_recording.id
            assignment.user_id = user_obj.id
            session.add(assignment)
            new_recording.update_status_upon_assignment_add_remove(session)
            session.commit()
    return new_recording


@routes_recording.route('/encounter/<encounter_id>/recording/<recording_id>/selection-table/add', methods=['POST'])
@require_live_session
@exclude_role_4
@login_required
def recording_selection_table_add(encounter_id,recording_id):
    """
    Given a selection table file in the POST request (selection-table-file), add it to the recording
    after validation. 
    """
    with Session() as session:
        try:
            recording = session.query(Recording).filter_by(id=recording_id).first()
            # If a selection file has been given, add it to the Recording object
            if 'selection-table-file' in request.files and request.files['selection-table-file'].filename != '':
                selection_table_file = request.files['selection-table-file'] # required in the POST request
                # Generate the destination filename and filepath for the selection table
                new_selection_table_filename = recording.generate_selection_table_filename()
                new_relative_path = recording.generate_relative_path()
                new_file = File()
                new_file.insert_path_and_filename(session, selection_table_file, new_relative_path, new_selection_table_filename, get_file_space_path())
                session.add(new_file)
                recording.selection_table_file = new_file 
                # Validate the selection table - if invalid then delete the selection table file
                error_msg = recording.validate_selection_table(session)
                
                recording.update_selection_traced_status(session)
                session.commit()
            else:
                handle_sqlalchemy_exception(session, Exception("The form did not send a selection table file."))
        except (Exception, SQLAlchemyError) as e:
            handle_sqlalchemy_exception(session, e)
        
    return redirect(url_for('recording.recording_view', recording_id=recording_id))
 
import csv
from flask import Response
from io import StringIO
@routes_recording.route('/export-selection-table/<recording_id>/<export_format>')
@require_live_session
@login_required
def export_selection_table(recording_id, export_format):
    """
    Export the selection table of a recording to a CSV or TSV file.
    """
    headers = ['Selection', 'View', 'Channel', 'Begin Time (s)', 'End Time (s)', 'Low Freq (Hz)', 'High Freq (Hz)', 'Delta Time (s)', 'Delta Freq (Hz)', 'Avg Power Density (dB FS/Hz)', 'Annotation']

    with Session() as session:
        selections = session.query(Selection).filter_by(recording_id=recording_id).all()
        recording = session.query(Recording).filter_by(id=recording_id).first()
        encounter = session.query(Encounter).filter_by(id=recording.encounter_id).first()
        csv_data = StringIO()
        if export_format == 'csv':
            writer = csv.writer(csv_data, delimiter=',')
        else:
            writer = csv.writer(csv_data, delimiter='\t')
        writer.writerow(headers)
        for selection in selections:
            writer.writerow([
                selection.id,
                selection.view,
                selection.channel,
                selection.begin_time,
                selection.end_time,
                selection.low_frequency,
                selection.high_frequency,
                selection.delta_time,
                selection.delta_frequency,
                selection.average_power,
                selection.annotation
            ])

        csv_data.seek(0)

        if export_format == 'csv':
            mimetype = 'text/csv'
            file_name = f'selection-table-{encounter.encounter_name}-rec-{recording.get_start_time_string()}.csv'
        else:
            mimetype = 'text/plain'
            file_name = f'selection-table-{encounter.encounter_name}-rec-{recording.get_start_time_string()}.txt'

        response = Response(csv_data.getvalue(), mimetype=mimetype, headers={'Content-Disposition': f'attachment; filename={file_name}'})
        return response


@routes_recording.route('/encounter/<encounter_id>/recording/<recording_id>/selection-table/delete', methods=['POST'])
@require_live_session
@exclude_role_4
@login_required
def recording_selection_table_delete(encounter_id, recording_id):
    """
    Delete the selection table file associated with the recording
    """
    with Session() as session:
        try:
            recording = session.query(Recording).filter_by(id=recording_id).first()
            file = session.query(File).filter_by(id=recording.selection_table_file_id).first()

            recording.reset_selection_table_values(session)
            recording.update_selection_traced_status(session)
            file.move_to_trash(session)
            recording.selection_table_file = None
            session.commit()
            flash(f'Deleted Selection Table', 'success')
        except SQLAlchemyError as e:
            handle_sqlalchemy_exception(session, e)
        except Exception as e:
            handle_sqlalchemy_exception(session, e)
        finally:
            return redirect(url_for('recording.recording_view', recording_id=recording_id))

@routes_recording.route('/encounter/<encounter_id>/recording/insert', methods=['POST'])
@require_live_session
@exclude_role_3
@exclude_role_4
@login_required
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
            handle_sqlalchemy_exception(session, e)
            return redirect(url_for('encounter.encounter_view', encounter_id=encounter_id))

    

@routes_recording.route('/recording/<recording_id>/view', methods=['GET'])
@login_required
def recording_view(recording_id):
    """
    Renders the recording view page for a specific encounter and recording.
    """
    
    if request.args.get('snapshot_date'):
        save_snapshot_date_to_session(request.args.get('snapshot_date'))

    with Session() as session:
        
        recording = shared_functions.create_system_time_request(session, Recording, {"id":recording_id}, one_result=True)
        

        #recording = query.filter_by(id=recording_id).first()
        selections = shared_functions.create_system_time_request(session, Selection, {"recording_id":recording_id}, order_by="selection_number")

        assigned_users = shared_functions.create_system_time_request(session, Assignment, {"recording_id":recording_id})
        
        logged_in_user_assigned = shared_functions.create_system_time_request(session, Assignment, {"user_id":current_user.id,"recording_id":recording_id})
        logged_in_user_assigned = logged_in_user_assigned[0] if len(logged_in_user_assigned) > 0 else None
        #recording_audit = session.query(RecordingAudit).filter_by(record_id=recording.id).all()
        from sqlalchemy.sql import select
        # Retrieve the historical records of a row
        
        #sql_query = session.query(Recording).filter_by(id=recording_id).all()

        recording_history = shared_functions.create_all_time_request(session, Recording, filters={"id":recording_id}, order_by="row_start")
        
        return render_template('recording/recording-view.html', recording=recording, selections=selections, user=current_user,recording_history=recording_history, assigned_users=assigned_users, logged_in_user_assigned=logged_in_user_assigned)

@routes_recording.route('/recording/<recording_id>/update_notes', methods=['POST'])
@require_live_session
@exclude_role_4
@login_required
def update_notes(recording_id):
    with Session() as session:
        recording = session.query(Recording).filter_by(id=recording_id).first()
        notes = request.form.get('notes')
        print(notes)
        
        recording.notes = notes
        print(recording.notes)
        session.commit()
        return redirect(url_for('recording.recording_view', recording_id=recording_id))  # Redirect to the recording view page


def flag_user_assignment(session, recording_id, user_id, completed_flag):
    recording = session.query(Recording).filter_by(id=recording_id).first()
    assignment = session.query(Assignment).filter_by(recording_id=recording_id).filter_by(user_id=user_id).first()
    if assignment is not None:
        assignment.completed_flag = completed_flag
        recording.update_status_upon_assignment_flag_change(session)
        session.commit()

@routes_recording.route('/recording/<recording_id>/<user_id>/flag-as-completed', methods=['GET'])
@require_live_session
@exclude_role_3
@exclude_role_4
@login_required
def flag_as_complete_for_user(recording_id, user_id):
    with Session() as session:
        flag_user_assignment(session, recording_id, user_id, True)
        return jsonify({'message': 'Success'})

@routes_recording.route('/recording/<recording_id>/<user_id>/unflag-as-completed', methods=['GET'])
@require_live_session
@exclude_role_3
@exclude_role_4
@login_required
def unflag_as_complete_for_user(recording_id, user_id):
    with Session() as session:
        flag_user_assignment(session, recording_id, user_id, False)
        return jsonify({'message': 'Success'})

@routes_recording.route('/recording/<recording_id>/unflag-as-completed', methods=['GET'])
@require_live_session
@exclude_role_3
@exclude_role_4
@login_required
def unflag_as_complete(recording_id):
    with Session() as session:
        recording = session.query(Recording).filter_by(id=recording_id).first()
        flag_user_assignment(session, recording_id, current_user.id, False)

        return redirect(url_for('recording.recording_view', recording_id=recording_id))

@routes_recording.route('/recording/<recording_id>/flag-as-completed', methods=['GET'])
@require_live_session
@exclude_role_3
@exclude_role_4
@login_required
def flag_as_complete(recording_id):
    with Session() as session:
        recording = session.query(Recording).filter_by(id=recording_id).first()
        flag_user_assignment(session, recording_id, current_user.id, True)
        return redirect(url_for('recording.recording_view', recording_id=recording_id))

@routes_recording.route('/recording/<recording_id>/update', methods=['POST'])
@require_live_session
@exclude_role_3
@exclude_role_4
@login_required
def recording_update(recording_id):
    """
    Updates a recording in the encounter with the specified encounter ID and recording ID.
    """
    with Session() as session:
        try:
            recording = session.query(Recording).filter_by(id=recording_id).first()
            recording_obj = insert_or_update_recording(session, request, recording.encounter_id, recording_id)
            recording_obj.update_call(session)
            session.commit()
            flash(f'Edited recording: {recording_obj.id}', 'success')                
            return redirect(url_for('recording.recording_view', recording_id=recording_id))
        except SQLAlchemyError as e:
            flash(parse_alchemy_error(e), 'error')
            session.rollback()
            return redirect(url_for('recording.recording_view', recording_id=recording_id))

@routes_recording.route('/encounter/<encounter_id>/recording/<recording_id>/delete', methods=['GET'])
@require_live_session
@exclude_role_3
@exclude_role_4
@login_required
def recording_delete(encounter_id,recording_id):
    """
    Function for deleting a recording of a given ID
    """
    with Session() as session:
        try:
            recording = session.query(Recording).filter_by(id=recording_id).first()
            recording.delete(session, keep_file_reference=True)
            session.commit()
            flash(f'Deleted recording: {recording.id}', 'success')
            return redirect(url_for('encounter.encounter_view', encounter_id=encounter_id))
        except SQLAlchemyError as e:
            flash(parse_alchemy_error(e), 'error')
            session.rollback()
            return redirect(url_for('encounter.encounter_view', encounter_id=encounter_id))

@routes_recording.route('/encounter/recording/<recording_id>/recording-file/<file_id>/delete',methods=['GET'])
@require_live_session
@exclude_role_3
@exclude_role_4
@login_required
def recording_file_delete(recording_id,file_id):
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
            return redirect(url_for('recording.recording_view', recording_id=recording_id))
        except SQLAlchemyError as e:
            flash(parse_alchemy_error(e), 'error')
            session.rollback()
            return redirect(url_for('recording.recording_view', recording_id=recording_id))

@routes_recording.route('/recording/<recording_id>/recording_delete_selections', methods=['DELETE'])
@require_live_session
@exclude_role_4
@login_required
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
    if not match:
        match = re.search(r'(\d{2})(\d{2})(\d{2})-(\d{2})(\d{2})(\d{2})', filename)
        if match:
            year = match.group(1)
            month = match.group(2)
            day = match.group(3)
            hour = match.group(4)
            minute = match.group(5)
            second = match.group(6)
            date_string = f"{day}/{month}/{year} {hour}:{minute}:{second}"
            date = datetime.strptime(date_string, '%d/%m/%y %H:%M:%S')


        

    return jsonify(date=date)

@routes_recording.route('/assign_recording/<user_id>/<recording_id>', methods=['GET'])
@require_live_session
@exclude_role_3
@exclude_role_4
@login_required
def assign_recording(user_id, recording_id):
    with Session() as session:
        try:
            recording = session.query(Recording).filter_by(id=recording_id).first()
            new_assignment = Assignment()
            new_assignment.user_id = user_id
            new_assignment.recording_id = recording_id
            session.add(new_assignment)
            session.flush()
            recording.update_status_upon_assignment_add_remove(session)
            session.commit()
            
        except Exception as e:
            handle_sqlalchemy_exception(session, e)
        return jsonify(success=True)
            

@routes_recording.route('/unassign_recording/<user_id>/<recording_id>', methods=['GET'])
@require_live_session
@exclude_role_3
@exclude_role_4
@login_required
def unassign_recording(user_id, recording_id):
    with Session() as session:
        try:
            recording = session.query(Recording).filter_by(id=recording_id).first()
            session.query(Assignment).filter_by(user_id=user_id, recording_id=recording_id).delete()
            recording.update_status_upon_assignment_add_remove(session)
            session.commit()
        except Exception as e:
            handle_sqlalchemy_exception(session, e)
        return jsonify(success=True)

@routes_recording.route('/recording/<recording_id>/recalculate-contour-statistics', methods=['GET'])
@login_required
@exclude_role_4
@require_live_session
def recalculate_contour_statistics(recording_id):
    counter = 0
    with Session() as session:
        try:
            import calculations.rocca.contour as contour_code
            selections = session.query(Selection).filter_by(recording_id=recording_id).all()
            for selection in selections:
                
                selection.reset_contour_stats()
                if selection.contour_file != None:
                    counter += 1
                    contour_file_obj = contour_code.ContourFile(selection.contour_file.get_full_absolute_path())
                    contour_file_obj.calculate_statistics(session, selection)
            session.commit()
            flash(f'Recalculated {counter} contour statistics', 'success')
        except Exception as e:
            handle_sqlalchemy_exception(session, e)
        return redirect(url_for('recording.recording_view', recording_id=recording_id))
    
import zipfile
import tempfile
import shutil

def zip_and_download_files(file_paths, zip_filename):
    with zipfile.ZipFile(zip_filename, 'w') as zipf:
        for file_path in file_paths:
            zipf.write(file_path, os.path.basename(file_path))
    
    return send_file(zip_filename, as_attachment=True)



def download_files(file_paths, file_names, zip_filename):
    with tempfile.TemporaryDirectory() as temp_dir:
        for file_path, file_name in zip(file_paths, file_names):
            if not file_name.endswith("."):
                file_extension = os.path.splitext(file_path)[1]
                new_file_name = f"{file_name}{file_extension}"
            else:
                new_file_name = file_name
            new_file_path = os.path.join(temp_dir, new_file_name)
            shutil.copy(file_path, new_file_path)
        
        return zip_and_download_files([os.path.join(temp_dir, file) for file in os.listdir(temp_dir)], zip_filename)
@routes_recording.route('/recording/<recording_id>/download-ctr-files', methods=['GET'])
@login_required
def download_ctr_files(recording_id):
    with Session() as session:
        recording = shared_functions.create_system_time_request(session, Recording, {"id":recording_id}, one_result=True)
        selections = shared_functions.create_system_time_request(session, Selection, {"recording_id":recording_id})
        ctr_files = [selection.ctr_file for selection in selections if selection.ctr_file is not None]
        file_names = [selection.generate_ctr_file_name() for selection in selections if selection.ctr_file is not None]
        # Download and zip the CTR files
        zip_filename = f"{recording.encounter.species.species_name}-{recording.encounter.encounter_name}-{recording.encounter.location}-{recording.start_time}_ctr_files.zip"
        file_paths = [ctr_file.get_full_absolute_path() for ctr_file in ctr_files]
        response = download_files(file_paths, file_names, zip_filename)
        
        return response
    
@routes_recording.route('/recording/<recording_id>/download-selection-files', methods=['GET'])
@login_required
def download_selection_files(recording_id):
    with Session() as session:
        selections = shared_functions.create_system_time_request(session, Selection, {"recording_id":recording_id})
        recording = shared_functions.create_system_time_request(session, Recording, {"id":recording_id}, one_result=True)
        selection_files = [selection.selection_file for selection in selections if selection.selection_file is not None]
        file_names = [selection.generate_filename() for selection in selections if selection.selection_file is not None]
        # Download and zip the CTR files
        zip_filename = f"{recording.encounter.species.species_name}-{recording.encounter.encounter_name}-{recording.encounter.location}-{recording.start_time}_selection_files.zip"
        file_paths = [selection_file.get_full_absolute_path() for selection_file in selection_files]
        response = download_files(file_paths, file_names, zip_filename)
        
        return response

@routes_recording.route('/recording/<recording_id>/download-contour-files', methods=['GET'])
@login_required
def download_contour_files(recording_id):
    with Session() as session:
        selections = shared_functions.create_system_time_request(session, Selection, {"recording_id":recording_id})
        recording = shared_functions.create_system_time_request(session, Recording, {"id":recording_id}, one_result=True)
        contour_files = [selection.contour_file for selection in selections if selection.contour_file is not None]
        file_names = [selection.generate_contour_filename() for selection in selections if selection.contour_file is not None]
        # Download and zip the CTR files
        zip_filename = f"{recording.encounter.species.species_name}-{recording.encounter.encounter_name}-{recording.encounter.location}-{recording.start_time}_contour_files.zip"
        file_paths = [contour_file.get_full_absolute_path() for contour_file in contour_files]
        response = download_files(file_paths, file_names, zip_filename)
        
    
        return response
    

@routes_recording.route('/recording/<recording_id>/download-recording-file', methods=['GET'])
@login_required
def download_recording_file(recording_id):
    with Session() as session:
        recording = shared_functions.create_system_time_request(session, Recording, {"id":recording_id}, one_result=True)
        file_name = recording.recording_file.get_full_absolute_path()
        download_file_name = recording.generate_recording_filename()

        return send_file(file_name, as_attachment=True, download_name=download_file_name)
@routes_recording.route('/recording/<recording_id>/mark_as_complete', methods=['GET'])
@require_live_session
@login_required
@exclude_role_3
@exclude_role_4
def mark_as_complete(recording_id):
    with Session() as session:
        recording = session.query(Recording).filter_by(id=recording_id).first()
        recording.set_status("Reviewed")
        session.commit()
        return redirect(url_for('recording.recording_view', recording_id=recording_id))

@routes_recording.route('/recording/<recording_id>/mark_as_on_hold', methods=['GET'])
@require_live_session
@login_required
@exclude_role_3
@exclude_role_4
def mark_as_on_hold(recording_id):
    with Session() as session:
        recording = session.query(Recording).filter_by(id=recording_id).first()
        recording.set_status("On Hold")
        session.commit()
        return redirect(url_for('recording.recording_view', recording_id=recording_id))