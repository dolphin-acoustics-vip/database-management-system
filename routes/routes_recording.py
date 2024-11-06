# Standard library imports
import pandas as pd
import uuid, os, re

# Third-party imports
from flask import Blueprint, flash,get_flashed_messages, jsonify, redirect,render_template,request, send_file, url_for, send_from_directory
from flask import session as client_session
from sqlalchemy.exc import SQLAlchemyError
from flask_login import login_user,login_required, current_user, login_manager
import csv
from flask import Response
from io import StringIO
from flask_socketio import emit, SocketIO
from flask_socketio import emit, SocketIO

# Local application imports
import database_handler
from database_handler import get_file_space_path, Session, save_snapshot_date_to_session, get_snapshot_date_from_session,require_live_session,exclude_role_1,exclude_role_2,exclude_role_3,exclude_role_4
import filespace_handler

from models import *
from exception_handler import *

routes_recording = Blueprint('recording', __name__)


# @routes_recording.route('/upload', methods=['POST'])
# def upload_file():
#     file = request.files['recording-file-input']
#     encounter_id = request.form['encounter_id']  # Process form data here as needed

#     # Stream the file in chunks
#     destination_path = os.path.join(get_file_space_path(), new_directory, new_filename)
#     chunk_size = 1024 * 1024  # 1MB chunks
    
#     with open(destination_path, 'wb') as f:
#         while True:
#             chunk = file.stream.read(chunk_size)
#             if not chunk:
#                 break
#             f.write(chunk)
#             emit('ping', {'message': 'Upload in progress...'}, to=request.sid)
    
#     # Optionally save other form data if needed here

#     return jsonify({'message': 'File uploaded successfully'})

def insert_or_update_recording(session, request, recording: Recording):
    """
    Insert or update a recording in the database. This function should be called
    by routes either inserting (new) Recording objects or updating (existing) 
    Recording objects.

    :param session: The database session
    :param request: The request object
    :param encounter_id: The id of the encounter
    :param recording_id: The id of the recording to be updated (default is None if inserting a new recording)

    :return: The Recording object that was inserted or updated
    """
    
    recording.set_start_time(request.form['time_start'])
    # If a recording file has been given, add it to the Recording object
    if 'recording_file_id' in request.form:
        recording_file_id = request.form['recording_file_id']
        recording_filename = request.form['recording_filename']
        recording_file = File()
        recording_file.insert_path_and_filename(session, filespace_handler.get_path_to_temporary_file(recording_file_id, recording_filename), recording.generate_relative_path(), recording.generate_recording_filename())
        filespace_handler.remove_temporary_file(recording_file_id, recording_filename)
        session.add(recording_file)
        recording.recording_file = recording_file
    filespace_handler.clean_filespace_temp()
    return recording


@routes_recording.route('/recording/<recording_id>/refresh-selection-table', methods=['POST'])
def refresh_selection_table(recording_id):
    with database_handler.get_session() as session:
        try:
            recording = session.query(Recording).filter_by(id=recording_id).first()
            recording.load_and_validate_selection_table()
            session.commit()
            recording.update_selection_traced_status()
        except (SQLAlchemyError,Exception) as e:
            exception_handler.handle_exception(session,e)
        return redirect(url_for('recording.recording_view', recording_id=recording_id))

@routes_recording.route('/encounter/<encounter_id>/recording/<recording_id>/selection-table/add', methods=['POST'])
@require_live_session
@exclude_role_4
@login_required
def recording_selection_table_add(encounter_id,recording_id):
    """
    Handles a POST request to upload a selection table for a given recording.

    :param encounter_id: the id of the encounter
    :type encounter_id: str
    :param recording_id: the id of the recording
    :type recording_id: str

    :return: a redirect to the recording view
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
                recording.load_and_validate_selection_table()
                session.commit()
                recording.update_selection_traced_status()
                
                flash("Selection table uploaded successfully", "success")
            else:
                raise WarningException("The form did not send a selection table file.")
        except (Exception, SQLAlchemyError) as e:
            handle_exception(session, e, prefix="Error adding selection table")
        
    return redirect(url_for('recording.recording_view', recording_id=recording_id))
 

@routes_recording.route('/export-selection-table/<recording_id>/<export_format>')
@require_live_session
@login_required
def export_selection_table(recording_id, export_format):
    """
    Export the selection table of a recording to a CSV or TSV file.
    """
    with database_handler.get_session() as session:
        try:
            recording = database_handler.create_system_time_request(session, Recording, {"id":recording_id}, one_result=True)
            return recording.export_selection_table(session, export_format)
        except (Exception, SQLAlchemyError) as e:
            handle_exception(session, e, prefix="Error exporting selection table")
            return redirect(url_for('recording.recording_view', recording_id=recording_id))
    with database_handler.get_session() as session:
        try:
            recording = database_handler.create_system_time_request(session, Recording, {"id":recording_id}, one_result=True)
            return recording.export_selection_table(session, export_format)
        except (Exception, SQLAlchemyError) as e:
            handle_exception(session, e, prefix="Error exporting selection table")
            return redirect(url_for('recording.recording_view', recording_id=recording_id))

@routes_recording.route('/recording/<recording_id>/selection-table/delete', methods=['POST'])
@routes_recording.route('/recording/<recording_id>/selection-table/delete', methods=['POST'])
@require_live_session
@exclude_role_4
@login_required
def recording_selection_table_delete(recording_id: str) -> Response:
    """
    Delete the selection table file associated with the recording.

    Args:
        recording_id (str): The ID of the recording to delete the selection table file for.

    Returns:
        Response: A redirect to the recording view page.
    """
    with Session() as session:
        try:
            recording = session.query(Recording).filter_by(id=recording_id).first()
            file = session.query(File).filter_by(id=recording.selection_table_file_id).first()
            recording.reset_selection_table_values(session)
            file.move_to_trash()
            recording.selection_table_file = None
            session.commit()
            recording.update_selection_traced_status()
            flash(f'Selection table deleted for {recording.get_unique_name()}', 'success')
        except (SQLAlchemyError,Exception) as e:
            handle_exception(session, e)
        finally:
            return redirect(url_for('recording.recording_view', recording_id=recording_id))

@routes_recording.route('/encounter/<encounter_id>/recording/insert', methods=['POST'])
@require_live_session
@exclude_role_3
@exclude_role_4
@login_required
def recording_insert(encounter_id: str) -> Response:
    """
    Inserts a new recording into the database for a given encounter ID.

    Args:
        encounter_id (str): The ID of the encounter to insert the recording into.
    
    Returns:
        flask.Response: The rendered template for the encounter view page.
    """
    
    with database_handler.get_session() as session:
        try:
            recording_obj = Recording(encounter_id=encounter_id)
            insert_or_update_recording(session, request, recording_obj)
            session.add(recording_obj)
            session.commit()
            flash(f'Recording inserted for {recording_obj.get_unique_name()}', 'success')
        except (SQLAlchemyError,Exception) as e:
            handle_exception(session, e, 'Error inserting recording')
        finally:
            return redirect(url_for('encounter.encounter_view', encounter_id=encounter_id))

@routes_recording.route('/recording/<recording_id>/view', methods=['GET'])
@login_required
def recording_view(recording_id: str) -> Response:
    """
    Renders the recording view page for a specific encounter and recording.

    Args:
        recording_id (str): The ID of the recording to view.
    
    Returns:
        flask.Response: The rendered template for the recording view page.
    """
    with Session() as session:
        recording = database_handler.create_system_time_request(session, Recording, {"id":recording_id}, one_result=True)
        selections = database_handler.create_system_time_request(session, Selection, {"recording_id":recording_id}, order_by="selection_number")
        assigned_users = database_handler.create_system_time_request(session, Assignment, {"recording_id":recording_id})
        logged_in_user_assigned = database_handler.create_system_time_request(session, Assignment, {"user_id":current_user.id,"recording_id":recording_id})
        logged_in_user_assigned = logged_in_user_assigned[0] if len(logged_in_user_assigned) > 0 else None
        recording_history = database_handler.create_all_time_request(session, Recording, filters={"id":recording_id}, order_by="row_start")
        return render_template('recording/recording-view.html', recording=recording, selections=selections, user=current_user,recording_history=recording_history, assigned_users=assigned_users, logged_in_user_assigned=logged_in_user_assigned)

@routes_recording.route('/recording/<recording_id>/update_notes', methods=['POST'])
@require_live_session
@exclude_role_4
@login_required
def update_notes(recording_id):
    with database_handler.get_session() as session:
        recording = session.query(Recording).filter_by(id=recording_id).first()
        notes = request.form.get('notes')
        recording.notes = notes.strip()
        recording.notes = notes.strip()
        session.commit()
        return redirect(url_for('recording.recording_view', recording_id=recording_id))  # Redirect to the recording view page


def flag_user_assignment(session, recording_id, user_id, completed_flag):
    """
    Update the completion status of a user's assignment for a recording.

    This function sets the `completed_flag` for a specified user's assignment
    associated with a given recording. It also updates the recording's status 
    based on the current assignment flags.

    Args:
        session (Session): The database session to use for the query.
        recording_id (str): The ID of the recording whose assignment is to be updated.
        user_id (str): The ID of the user whose assignment is to be updated.
        completed_flag (bool): The flag indicating whether the assignment is completed.
    """
    recording = session.query(Recording).filter_by(id=recording_id).first()
    assignment = session.query(Assignment).filter_by(recording_id=recording_id).filter_by(user_id=user_id).first()
    if assignment is not None:
        assignment.completed_flag = completed_flag
        session.commit()
        recording.update_status()
        session.commit()

@routes_recording.route('/recording/flag-as-completed-for-user', methods=['GET'])
@require_live_session
@exclude_role_3
@exclude_role_4
@login_required
def flag_as_complete_for_user():
    """
    Given a user_id and recording_id, if an assignment exists for the user and recording,
    flag the assignment as complete. This route will also update the provided recording
    status - see Recording.status_update()

    Args:
        recording_id (_type_): The ID of the recording of the assignment.
        user_id (_type_): The ID of the user of the assignment
    """
    recording_id = utils.extract_args('recording_id')
    user_id = utils.extract_args('user_id')
    with database_handler.get_session() as session:
        flag_user_assignment(session, recording_id, user_id, True)
        return jsonify({'message': 'Success'}), 200

@routes_recording.route('/recording/unflag-as-completed-for-user', methods=['GET'])
@require_live_session
@exclude_role_3
@exclude_role_4
@login_required
def unflag_as_complete_for_user():
    """
    Given a user_id and recording_id, if an assignment exists for the user and recording,
    flag the assignment as incomplete. This route will also update the provided recording
    status - see Recording.status_update()

    Args:
        recording_id (_type_): The ID of the recording of the assignment.
        user_id (_type_): The ID of the user of the assignment
    """
    recording_id = utils.extract_args('recording_id')
    user_id = utils.extract_args('user_id')
    with database_handler.get_session() as session:
        flag_user_assignment(session, recording_id, user_id, False)
        return jsonify({'message': 'Success'})

@routes_recording.route('/recording/unflag-as-completed', methods=['POST'])
@require_live_session
@exclude_role_4
@login_required
def unflag_as_complete():
    """
    If a user assignment exists for the current logged in user and the recording passed
    as an argument, flag it as incomplete. This route will also update the provided
    recording status - see Recording.status_update()

    Args:
        recording_id (str): The ID of the recording to flag.

    Returns:
        : redirect to the referring page.
    """
    recording_id = utils.extract_args('recording_id')
    with database_handler.get_session() as session:
        flag_user_assignment(session, recording_id, current_user.id, False)
        return redirect(request.referrer)

@routes_recording.route('/recording/flag-as-completed', methods=['POST'])
@require_live_session
@exclude_role_4
@login_required
def flag_as_complete():
    """
    If a user assignment exists for the current logged in user and the recording passed
    as an argument, flag it as complete. This route will also update the provided
    recording status - see Recording.status_update()

    Args:
        recording_id (str): The ID of the recording to flag.

    Returns:
        : redirect to the referring page.
    """
    recording_id = utils.extract_args('recording_id')
    with database_handler.get_session() as session:
        flag_user_assignment(session, recording_id, current_user.id, True)
        return redirect(request.referrer)

@routes_recording.route('/recording/<recording_id>/update', methods=['POST'])
@require_live_session
@exclude_role_3
@exclude_role_4
@login_required
def recording_update(recording_id):
    """
    Updates a recording in the encounter with the specified encounter ID and recording ID.
    """
    with database_handler.get_session() as session:
        try:
            recording_obj = session.query(Recording).with_for_update().filter_by(id=recording_id).first()
            insert_or_update_recording(session, request, recording_obj)
            session.commit()
            flash(f'Recording updated for {recording_obj.get_unique_name()}', 'success')
            recording_obj.update_call()
            return redirect(url_for('recording.recording_view', recording_id=recording_id))
        except (SQLAlchemyError,Exception) as e:
            exception_handler.handle_exception(session,e)
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
            if recording:
                recording.delete_children(keep_file_reference=True)
                session.delete(recording)
                session.commit()
                flash(f'Deleted recording: {recording.get_unique_name()}', 'success')
        except (Exception,SQLAlchemyError) as e:
            handle_exception(session, e)
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
            file.delete()
            session.commit()
            flash(f'Deleted recording file for {recording.get_unique_name()}', 'success')
        except (Exception,SQLAlchemyError) as e:
            handle_exception(session, e)
        return redirect(url_for('recording.recording_view', recording_id=recording_id))

@routes_recording.route('/recording/recording_delete_selections', methods=['DELETE'])
@require_live_session
@exclude_role_4
@login_required
def recording_delete_selections():
    """
    Bulk delete selections from the database.

    :param selectionIds: A JSON list of selection IDs to delete.

    Expects a JSON payload with a list of selection IDs under the key "selectionIds".
    Returns a JSON response with a message indicating the number of selections deleted.
    """
    data = request.get_json()

    selection_ids = data.get('selectionIds', [])
    if selection_ids == None or len(selection_ids) == 0:
        handle_exception(session, WarningException('No selections selected for deletion.'))
    
    with Session() as session:
        counter=0
        for selection_id in selection_ids:
            try:
                selection = session.query(Selection).filter_by(id=selection_id).first()
                selection.delete_children()
                session.delete(selection)

                session.commit()
                counter += 1
            except (SQLAlchemyError,Exception) as e:
                handle_exception(session,e,prefix="Error deleting selection")
        flash(f'Deleted {counter} selections', 'success')
        return jsonify({'message': 'Bulk delete completed'}), 200


  

@routes_recording.route('/encounter/extract_date', methods=['GET'])
def extract_date():
    """
    Extracts a date from a filename.
    
    :param filename: The filename to extract the date from, as an argument in the request.
    :type filename: str
    :return date: The date extracted from the filename in JSON format {date:value}, or {date:None}.
    """
    filename = request.args.get('filename')
    date = database_handler.parse_date(filename)
    return jsonify(date=date)

@routes_recording.route('/assign_recording', methods=['GET'])
@require_live_session
@exclude_role_3
@exclude_role_4
@login_required
def assign_recording():
    """Create an assignment between a user and a recording.

    Args:
        user_id (str): The ID of the user to assign the recording to.
        recording_id (str): The ID of the recording to assign.

    Returns:
        _type_: _description_
    """
    user_id = utils.extract_args('user_id')
    recording_id = utils.extract_args('recording_id')
    with database_handler.get_session() as session:
        try:
            assignment = Assignment(recording_id=recording_id, user_id=user_id)
            session.add(assignment)
            session.commit()
            assignment = Assignment(recording_id=recording_id, user_id=user_id)
            session.add(assignment)
            session.commit()
            recording = session.query(Recording).filter_by(id=recording_id).first()
            recording.update_status()
            session.commit()      
        except (SQLAlchemyError,Exception) as e:
            handle_sqlalchemy_exception(session, e)


@routes_recording.route('/unassign_recording', methods=['GET'])
@require_live_session
@exclude_role_3
@exclude_role_4
@login_required
def unassign_recording():
    """
    Unassigns a recording from a user.

    :param user_id: The ID of the user to unassign the recording from.
    :type user_id: str
    :param recording_id: The ID of the recording to unassign.
    :type recording_id: str
    :return: A JSON object with a single key, 'success', with a value of True if successful, False otherwise.
    :rtype: dict
    """
    user_id = request.args.get('user_id')
    recording_id = request.args.get('recording_id')
    with database_handler.get_session() as session:
        try:
            recording = session.query(Recording).filter_by(id=recording_id).first()
            assignment = session.query(Assignment).filter_by(user_id=user_id).filter_by(recording_id=recording_id).first()
            session.delete(assignment)
            session.commit()
            recording = session.query(Recording).filter_by(id=recording_id).first()
            recording.update_status()
            session.commit()
        except (SQLAlchemyError,Exception) as e:
            handle_sqlalchemy_exception(session, e)



import contour_statistics

def recalculate_contour_statistics(session, selection):
    """
    Recalculate contour statistics for the given selection.

    :param session: The current sqlalchemy session
    :type session: sqlalchemy.orm.session.Session
    :param selection: The selection object to recalculate the contour statistics for
    :type selection: Selection
    """
    selection.reset_contour_stats()
    if selection and selection.contour_file is not None:
        contour_file_obj = contour_statistics.ContourFile(selection.contour_file.get_full_absolute_path(),selection.selection_number)
        contour_rows = contour_file_obj.calculate_statistics(session, selection)
        selection.generate_ctr_file(session, contour_rows)

@routes_recording.route('/selection/<selection_id>/recalculate-contour-statistics', methods=['GET'])
@login_required
@exclude_role_4
@require_live_session
def recalculate_contour_statistics_for_selection(selection_id):
    with database_handler.get_session() as session:
        try:
            selection = session.query(Selection).filter_by(id=selection_id).first()
            selection.recalculate_contour_statistics(session)
            session.commit()
            flash(f"Refreshed contour statistics for {selection.get_unique_name()}", 'success')
        except (Exception, SQLAlchemyError) as e:
            handle_exception(session, e, prefix="Error refreshing contour statistics")
    return redirect(request.referrer)

@routes_recording.route('/recording/<recording_id>/recalculate-contour-statistics', methods=['GET'])
@login_required
@exclude_role_4
@require_live_session
def recalculate_contour_statistics_for_recording(recording_id):
    """
    Recalculates the contour statistics for all selections associated with the recording specified by recording_id.

    :param recording_id: The ID of the recording to recalculate contour statistics for.
    :type recording_id: str
    :return: Redirects to the recording view page.
    :rtype: flask.Response
    """
    counter = 0

    with database_handler.get_session() as session:
        # no with_for_update() as this session/query is only for SELECT (no updates)
        selections = session.query(Selection).filter_by(recording_id=recording_id).all()
        selection_ids = [selection.id for selection in selections]
        session.close()
    
    for selection_id in selection_ids:
        try:
            # need to query selection in new session to atomise transaction
            with database_handler.get_session() as selection_session:
                selection = selection_session.query(Selection).with_for_update().filter_by(id=selection_id).first()
                selection.recalculate_contour_statistics(selection_session)
                selection_session.commit()
                counter += 1
                selection_session.close()
            selection_session = None
        except (Exception, SQLAlchemyError) as e:
            handle_exception(selection_session, e)
    flash(f'Recalculated {counter} contour statistics.', 'success')
    return redirect(url_for('recording.recording_view', recording_id=recording_id))
    


import zipfile
import tempfile
import shutil
from database_handler import get_tempdir


@routes_recording.route('/recording/<recording_id>/download-ctr-files', methods=['GET'])
@login_required
def download_ctr_files(recording_id):
    with Session() as session:
        recording = database_handler.create_system_time_request(session, Recording, {"id":recording_id}, one_result=True)
        selections = database_handler.create_system_time_request(session, Selection, {"recording_id":recording_id})
        ctr_files = [selection.ctr_file for selection in selections if selection.ctr_file is not None]
        file_names = [selection.generate_ctr_file_name() for selection in selections if selection.ctr_file is not None]
        zip_filename = f"{recording.encounter.species.species_name}-{recording.encounter.encounter_name}-{recording.encounter.location}-{recording.start_time}_ctr_files.zip"
        file_paths = [ctr_file.get_full_absolute_path() for ctr_file in ctr_files]
        response = utils.download_files(file_paths, file_names, zip_filename)
        
        return response
    
@routes_recording.route('/recording/<recording_id>/download-selection-files', methods=['GET'])
@login_required
def download_selection_files(recording_id):
    """
    Handles a GET request to download all selection files associated with a given recording.
    
    :param recording_id: the id of the recording
    :type recording_id: str
    :return: a zip file containing all selection files
    :rtype: flask.Response
    """
    with Session() as session:
        selections = database_handler.create_system_time_request(session, Selection, {"recording_id":recording_id})
        recording = database_handler.create_system_time_request(session, Recording, {"id":recording_id}, one_result=True)
        selection_files = [selection.selection_file for selection in selections if selection.selection_file is not None]
        file_names = [selection.generate_selection_filename() for selection in selections if selection.selection_file is not None]
        zip_filename = f"{recording.encounter.species.species_name}-{recording.encounter.encounter_name}-{recording.encounter.location}-{recording.start_time}_selection_files.zip"
        file_paths = [selection_file.get_full_absolute_path() for selection_file in selection_files]
        response = utils.download_files(file_paths, file_names, zip_filename)
        return response

@routes_recording.route('/recording/<recording_id>/download-contour-files', methods=['GET'])
@login_required
def download_contour_files(recording_id):
    """
    Handles a GET request to download all contour files associated with a given recording.
    
    :param recording_id: the id of the recording
    :type recording_id: str
    :return: a JSON response with a success message if the files are downloaded successfully
    """
    with Session() as session:
        selections = database_handler.create_system_time_request(session, Selection, {"recording_id":recording_id})
        recording = database_handler.create_system_time_request(session, Recording, {"id":recording_id}, one_result=True)
        contour_files = [selection.contour_file for selection in selections if selection.contour_file is not None]
        file_names = [selection.generate_contour_filename() for selection in selections if selection.contour_file is not None]
        zip_filename = f"{recording.encounter.species.species_name}-{recording.encounter.encounter_name}-{recording.encounter.location}-{recording.start_time}_contour_files.zip"
        file_paths = [contour_file.get_full_absolute_path() for contour_file in contour_files]
        response = utils.download_files(file_paths, file_names, zip_filename)
        return response
    
@routes_recording.route('/recording/<recording_id>/download-recording-file', methods=['GET'])
@login_required
def download_recording_file(recording_id):
    with Session() as session:
        recording = database_handler.create_system_time_request(session, Recording, {"id":recording_id}, one_result=True)
        return utils.download_file(recording.recording_file, recording.generate_recording_filename)

    
@routes_recording.route('/recording/<recording_id>/mark_as_complete', methods=['GET'])
@require_live_session
@login_required
@exclude_role_3
@exclude_role_4
def mark_as_complete(recording_id):
    """
    Marks a recording as complete. This is only accessible by users with Role 1 or 2.
    A recording can be marked as complete if it has been reviewed and is ready to be
    used for analysis. When a recording is marked as complete, it will be displayed
    in the recording view as having a status of 'Reviewed'.

    :param recording_id: the id of the recording
    :type recording_id: str
    :return: a redirect to the recording view
    """
    with Session() as session:
        recording = session.query(Recording).filter_by(id=recording_id).first()
        recording.set_status_reviewed()
        session.commit()
        return redirect(url_for('recording.recording_view', recording_id=recording_id))

@routes_recording.route('/recording/<recording_id>/mark_as_on_hold', methods=['GET'])
@require_live_session
@login_required
@exclude_role_3
@exclude_role_4
def mark_as_on_hold(recording_id):
    """
    Marks a recording as on hold. This is only accessible by users with Role 1 or 2.
    A recording can be marked as on hold if it needs to be reviewed or modified before
    it can be used for analysis. When a recording is marked as on hold, it will be
    displayed in the recording view as having a status of 'On Hold'.

    :param recording_id: the id of the recording
    :type recording_id: str
    :return: a redirect to the recording view
    """
    with Session() as session:
        recording = session.query(Recording).filter_by(id=recording_id).first()
        recording.set_status_on_hold()
        session.commit()
        return redirect(url_for('recording.recording_view', recording_id=recording_id))