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

# Third-party imports
from flask import Blueprint, Response, flash, jsonify, redirect, render_template, url_for, request
from sqlalchemy.exc import SQLAlchemyError
from flask_login import login_required, current_user

# Local application imports
from .. import database_handler
from .. import filespace_handler
from .. import models
from .. import exception_handler
from .. import utils
from .. import contour_statistics
from .. import response_handler

routes_recording = Blueprint('recording', __name__)


def check_editable(recording: models.Recording):
    if recording.is_reviewed() or recording.is_on_hold():
        if current_user.role.id == 3 or current_user.role.id == 4:
            raise exception_handler.WarningException("You do not have permission to edit this recording.")

@routes_recording.route('/recording/<recording_id>/check-editable', methods=['POST'])
def check_editable_recording(recording_id):
    response = response_handler.JSONResponse()
    with database_handler.get_session() as session:
        try:
            recording = session.query(models.Recording).filter_by(id=recording_id).first()
            check_editable(recording)
            response.data['editable'] = 1
        except (Exception, SQLAlchemyError) as e:
            response.add_error(exception_handler.handle_exception(exception=e, session=session, show_flash=False))
    return response.to_json()

def insert_or_update_recording(session, request, recording: models.Recording):
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
    session.flush()
    # If a recording file has been given, add it to the Recording object
    if 'recording_file_id' in request.form and request.form['recording_file_id'] != "":
        recording_file_id = request.form['recording_file_id']
        recording_filename = request.form['recording_filename']
        recording_file = models.File()
        recording_file.insert_path_and_filename(session, filespace_handler.get_complete_temporary_file(recording_file_id, recording_filename), recording.generate_relative_directory(), recording.recording_file_name)
        filespace_handler.remove_temporary_file(recording_file_id, recording_filename)
        if recording_file.extension != "wav": raise exception_handler.WarningException(f"Recording needs to be of type 'wav' but is '{recording_file.extension}'")
        session.add(recording_file)
        recording.set_recording_file(recording_file)
    filespace_handler.clean_filespace_temp()
    return recording

@routes_recording.route('/recording/<recording_id>/selection-table/refresh', methods=['POST'])
def selection_table_refresh(recording_id):
    response = response_handler.JSONResponse()
    with database_handler.get_session() as session:
        try:
            recording = session.query(models.Recording).filter_by(id=recording_id).first()
            recording.selection_table_apply(session)
            session.flush()
            recording.update_selection_traced_status(session)
            session.commit()
            response.set_redirect(request.referrer)
        except Exception as e:
            response.add_error(exception_handler.handle_exception(exception=e, session=session, show_flash=False))
    return response.to_json()

@routes_recording.route('/recording/<recording_id>/selection-table/insert', methods=['POST'])
@database_handler.require_live_session
@database_handler.exclude_role_4
@login_required
def selection_table_insert(recording_id):
    response = response_handler.JSONResponse()
    with database_handler.get_session() as session:
        try:
            recording = session.query(models.Recording).filter_by(id=recording_id).first()
            check_editable(recording)
            if 'selection-table-file' in request.files and request.files['selection-table-file'].filename != '':
                new_file = models.File()
                new_file.insert_path_and_filename(request.files['selection-table-file'], recording.relative_directory, recording.selection_table_file_name)
                session.add(new_file)
                recording.selection_table_file = new_file 
                session.flush()
                recording.selection_table_apply(session)
                session.flush()
                recording.update_selection_traced_status(session)
                session.commit()
                flash("Selection table uploaded successfully", "success")
                response.set_redirect(request.referrer)
            else:
                response.add_error("The form did not send a selection table file.")
        except Exception as e:
            response.add_error(exception_handler.handle_exception(exception=e, prefix="Unable to upload selection table", session=session, show_flash=False))
    return response.to_json()
 

@routes_recording.route('/export-selection-table/<recording_id>/<export_format>')
@database_handler.require_live_session
@login_required
def selection_table_export(recording_id, export_format):
    """
    Export the selection table of a recording to a CSV or TSV file.
    """
    with database_handler.get_session() as session:
        try:
            recording = database_handler.create_system_time_request(session, models.Recording, {"id":recording_id}, one_result=True)
            return recording.selection_table_export(session, export_format)
        except (Exception, SQLAlchemyError) as e:
            exception_handler.handle_exception(exception=e, prefix="Error exporting selection table", session=session)
            return redirect(url_for('recording.recording_view', recording_id=recording_id))
    with database_handler.get_session() as session:
        try:
            recording = database_handler.create_system_time_request(session, models.Recording, {"id":recording_id}, one_result=True)
            return recording.selection_table_export(session, export_format)
        except (Exception, SQLAlchemyError) as e:
            exception_handler.handle_exception(exception=e, prefix="Error exporting selection table", session=session)
            return redirect(url_for('recording.recording_view', recording_id=recording_id))

@routes_recording.route('/recording/<recording_id>/selection-table/delete', methods=['POST'])
@database_handler.require_live_session
@database_handler.exclude_role_4
@login_required
def selection_table_delete(recording_id: str) -> Response:
    with database_handler.get_session() as session:
        try:
            recording = session.query(models.Recording).filter_by(id=recording_id).first()
            file = session.query(models.File).filter_by(id=recording.selection_table_file_id).first()
            recording.selection_table_data_delete(session)
            file.move_to_trash()
            recording.selection_table_file = None
            session.flush()
            recording.update_selection_traced_status(session)
            session.commit()
            flash(f'Deleted selection table from {recording.unique_name}.', 'success')
            return redirect(url_for('recording.recording_view', recording_id=recording_id))
        except (SQLAlchemyError,Exception) as e:
            exception_handler.handle_exception(exception=e, session=session)
            return redirect(request.referrer)            

@routes_recording.route('/encounter/<encounter_id>/recording/insert', methods=['POST'])
@database_handler.require_live_session
@database_handler.exclude_role_3
@database_handler.exclude_role_4
@login_required
def recording_insert(encounter_id: str) -> Response:
    response = response_handler.JSONResponse()
    with database_handler.get_session() as session:
        try:
            recording = models.Recording()
            recording.encounter = session.query(models.Encounter).filter_by(id=encounter_id).first()
            session.add(recording)
            recording.insert(request.form)
            session.commit()
            flash(f'Inserted {recording.unique_name}.', 'success')
            response.set_redirect(url_for('encounter.encounter_view', encounter_id=encounter_id))
        except Exception as e:
            response.add_error(exception_handler.handle_exception(exception=e, prefix="Error inserting recording", session=session, show_flash=False))
    return response.to_json()

@routes_recording.route('/recording/<recording_id>/view', methods=['GET'])
@login_required
def recording_view(recording_id: str) -> Response:
    with database_handler.get_session() as session:
        recording = database_handler.create_system_time_request(session, models.Recording, {"id":recording_id}, one_result=True)
        selections = database_handler.create_system_time_request(session, models.Selection, {"recording_id":recording_id}, order_by="selection_number")
        assigned_users = database_handler.create_system_time_request(session, models.Assignment, {"recording_id":recording_id})
        logged_in_user_assigned = database_handler.create_system_time_request(session, models.Assignment, {"user_id":current_user.id,"recording_id":recording_id})
        logged_in_user_assigned = logged_in_user_assigned[0] if len(logged_in_user_assigned) > 0 else None
        recording_history = database_handler.create_all_time_request(session, models.Recording, filters={"id":recording_id}, order_by="row_start")
        return render_template('recording/recording-view.html', recording=recording, selections=selections, user=current_user,recording_history=recording_history, assigned_users=assigned_users, logged_in_user_assigned=logged_in_user_assigned)

@routes_recording.route('/recording/<recording_id>/update_notes', methods=['POST'])
@database_handler.require_live_session
@database_handler.exclude_role_4
@login_required
def update_notes(recording_id):
    response = response_handler.JSONResponse()
    with database_handler.get_session() as session:
        try:
            recording = session.query(models.Recording).filter_by(id=recording_id).first()
            check_editable(recording)
            notes = request.form.get('notes')
            recording.notes = notes.strip()
            recording.notes = notes.strip()
            session.commit()
            response.add_message("Notes updated successfully.")
        except (Exception, SQLAlchemyError) as e:
            response.add_error(exception_handler.handle_exception(exception=e, prefix="Error updating notes", session=session, show_flash=False))
        return response.to_json()


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
    recording = session.query(models.Recording).filter_by(id=recording_id).first()
    assignment = session.query(models.Assignment).filter_by(recording_id=recording_id).filter_by(user_id=user_id).first()
    if assignment is not None:
        assignment.completed_flag = completed_flag
        session.commit()
        recording.update_status()
        session.commit()

@routes_recording.route('/recording/flag-as-completed-for-user', methods=['GET'])
@database_handler.require_live_session
@database_handler.exclude_role_3
@database_handler.exclude_role_4
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
@database_handler.require_live_session
@database_handler.exclude_role_3
@database_handler.exclude_role_4
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
@database_handler.require_live_session
@database_handler.exclude_role_4
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
@database_handler.require_live_session
@database_handler.exclude_role_4
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
@database_handler.require_live_session
@database_handler.exclude_role_3
@database_handler.exclude_role_4
@login_required
def recording_update(recording_id: str) -> Response:
    """Updates a recording in the encounter with the specified encounter ID and recording ID.

    Args:
        recording_id (str): The ID of the recording to update.

    Returns:
        flask.Response: redirect to the referring page.
    """
    # Create a response with redirect to the referring page
    response = response_handler.JSONResponse(redirect=request.referrer)
    with database_handler.get_session() as session:
        try:
            recording_obj = session.query(models.Recording).with_for_update().filter_by(id=recording_id).first()
            check_editable(recording_obj)
            recording_obj.update(request.form)
            recording_obj.apply_updates()
            session.commit()
            flash(f'Updated {recording_obj.unique_name}.', 'success')
            recording_obj.update_call()
            return response.to_json()
        except (SQLAlchemyError,Exception) as e:
            response.add_error(exception_handler.handle_exception(exception=e, session=session, show_flash=False))
            response.set_redirect(None)
            return response.to_json()

@routes_recording.route('/encounter/<encounter_id>/recording/<recording_id>/delete', methods=['POST'])
@database_handler.require_live_session
@database_handler.exclude_role_3
@database_handler.exclude_role_4
@login_required
def recording_delete(encounter_id,recording_id):
    """
    Function for deleting a recording of a given ID
    """
    response = response_handler.JSONResponse()
    with database_handler.get_session() as session:
        try:
            recording = session.query(models.Recording).filter_by(id=recording_id).first()
            if recording:
                unique_name = recording.unique_name
                recording.delete()
                session.delete(recording)
                session.commit()
                flash(f'Deleted {unique_name}.', 'success')
            response.set_redirect(url_for("encounter.encounter_view", encounter_id=encounter_id))
            return response.to_json()
        except (Exception,SQLAlchemyError) as e:
            response.add_error(exception_handler.handle_exception(exception=e, session=session, show_flash=False))
            return response.to_json()

@routes_recording.route('/encounter/recording/<recording_id>/recording-file/<file_id>/delete',methods=['GET'])
@database_handler.require_live_session
@database_handler.exclude_role_3
@database_handler.exclude_role_4
@login_required
def recording_file_delete(recording_id,file_id):
    """
    A function for deleting a recording file of a given ID
    """
    with database_handler.get_session() as session:
        try:
            recording = session.query(models.Recording).filter_by(recording_file_id=file_id).first()
            # Remove recording file reference from recording
            recording.recording_file=None
            # Delete the File object for the recording file its self
            file = session.query(models.File).filter_by(id=file_id).first()
            file.delete()
            session.commit()
            flash(f'Deleted recording file from {recording.unique_name}.', 'success')
            return redirect(url_for('recording.recording_view', recording_id=recording_id))
        except (Exception,SQLAlchemyError) as e:
            exception_handler.handle_exception(exception=e, session=session)
            return redirect(request.referrer)
        

@routes_recording.route('/recording/recording_delete_selections', methods=['DELETE'])
@database_handler.require_live_session
@database_handler.exclude_role_4
@login_required
def recording_delete_selections():
    """ 
    Function for deleting multiple selections of a recording. If no changes are made (either
    because `selectionIds` is empty or `selectionIds` is not empty but all deletions fail) then
    no redirect link is given, and errors are returned in the response_handler.JSONResponse object.

    If `selectionIds` are given and any are successful, then a redirect link is given. Any failures
    are added to the response_handler.JSONResponse object.

    Note that this method requires `selectionIds` to be passed to the data.

    Returns:
        flask.Response: the response object (see response_handler.JSONResponse)
    """
    response = response_handler.JSONResponse()


    data = request.get_json()

    selection_ids = data.get('selectionIds', [])
    if selection_ids == None or len(selection_ids) == 0:
        response.add_error('No selections selected for deletion.')
        return response.to_json()
    
    with database_handler.get_session() as session:
        counter=0
        for selection_id in selection_ids:
            selection = None
            try:
                selection = session.query(models.Selection).filter_by(id=selection_id).first()
                recording = session.query(models.Recording).filter_by(id=selection.recording_id).first()
                check_editable(recording)
                selection.delete_children()
                session.delete(selection)
                session.commit()
                counter += 1
            except (SQLAlchemyError,Exception) as e:
                response.add_error(exception_handler.handle_exception(exception=e,prefix=f"Error deleting selection {selection.selection_number if selection else ''}", session=session, show_flash=False))
        if counter > 0:
            flash(f'Deleted {counter} selections.', 'success')
            response.set_redirect(request.referrer)
        else:
            response.add_error(f'No selections deleted.')
        return response.to_json()


  

@routes_recording.route('/encounter/extract_date', methods=['GET', 'POST'])
def extract_date():
    """
    Extracts a date from a filename.
    
    :param filename: The filename to extract the date from, as an argument in the request.
    :type filename: str
    :return date: The date extracted from the filename in JSON format {date:value}, or {date:None}.
    """
    response = response_handler.JSONResponse()
    try:
        filename = request.form.get('filename')
        date = database_handler.parse_date(filename)
        if not date:
            response.add_error('No date found in filename.')
        else:
            response.add_message('Date found in filename.')
        response.data['date'] = date
    except (Exception) as e:
        response.add_error(exception_handler.handle_exception(exception=e, session=None, show_flash=False))
    return response.to_json()

@routes_recording.route('/assign_recording', methods=['GET'])
@database_handler.require_live_session
@database_handler.exclude_role_3
@database_handler.exclude_role_4
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
            assignment = models.Assignment(recording_id=recording_id, user_id=user_id)
            session.add(assignment)
            session.commit()
            assignment = models.Assignment(recording_id=recording_id, user_id=user_id)
            session.add(assignment)
            session.commit()
            recording = session.query(models.Recording).filter_by(id=recording_id).first()
            recording.update_status()
            session.commit()      
        except (SQLAlchemyError,Exception) as e:
            exception_handler.handle_exception(exception=e, session=session)


@routes_recording.route('/unassign_recording', methods=['GET'])
@database_handler.require_live_session
@database_handler.exclude_role_3
@database_handler.exclude_role_4
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
            recording = session.query(models.Recording).filter_by(id=recording_id).first()
            assignment = session.query(models.Assignment).filter_by(user_id=user_id).filter_by(recording_id=recording_id).first()
            session.delete(assignment)
            session.commit()
            recording = session.query(models.Recording).filter_by(id=recording_id).first()
            recording.update_status()
            session.commit()
        except (SQLAlchemyError,Exception) as e:
            exception_handler.handle_exception(exception=e, session=session)



@routes_recording.route('/recording/<recording_id>/recalculate-contour-statistics', methods=['POST'])
@login_required
@database_handler.exclude_role_4
@database_handler.require_live_session
def recalculate_contour_statistics_for_recording(recording_id: str):
    """Recalculates the contour statistics for all selections associated with the recording specified by recording_id.
    Any errors processing contours will not halt the recalculation - it will merely be skipped and an error message added
    to the response (see response_handler.JSONResponse).

    Args:
        recording_id (str): The ID of the recording to recalculate contour statistics for.

    Returns:
        flask.Response: A JSON response containing the updated recording and any errors that occurred.
    """
    response = response_handler.JSONResponse()

    # First collect all the selections in the recording
    with database_handler.get_session() as session:
        # Preamble - checking the user has permissions to edit the recording and collecting
        # all selections of the recording
        try:
            recording = session.query(models.Recording).filter_by(id=recording_id).first()
            check_editable(recording)
            selections = session.query(models.Selection).filter_by(recording_id=recording_id).all()
        except (Exception, SQLAlchemyError) as e:
            response.add_error(exception_handler.handle_exception(exception=e, session=session, show_flash=False))
            return response.to_json()
        
        count = 0
        for selection in selections:
            try:
                # Check if the user has permission to edit the selection
                recording = session.query(models.Recording).filter_by(id=selection.recording_id).first()
                check_editable(recording)
                from .routes_selection import generate_ctr_file
                generate_ctr_file(session, selection.id)
                selection.recalculate_contour_statistics()
                session.commit()
                count += 1
            except (Exception, SQLAlchemyError) as e:
                # A ValueError from Selection.recalculate_contour_statistics() occurs when the contour file is missing
                if type(e) == ValueError: e = exception_handler.WarningException(e.args[0])
                response.add_error(exception_handler.handle_exception(exception=e, session=session, show_flash=False))
    
    response.add_message(f"{count} contour statistic(s) and CTR file(s) were regenerated.")
    return response.to_json()
    

@routes_recording.route('/recording/<recording_id>/download-ctr-files', methods=['GET'])
@login_required
def download_ctr_files(recording_id):
    with database_handler.get_session() as session:
        recording = database_handler.create_system_time_request(session, models.Recording, {"id":recording_id}, one_result=True)
        selections = database_handler.create_system_time_request(session, models.Selection, {"recording_id":recording_id})
        ctr_files = [selection.ctr_file for selection in selections if selection.ctr_file is not None]
        file_names = [selection.generate_ctr_file_name() for selection in selections if selection.ctr_file is not None]
        zip_filename = f"{recording.encounter.species.species_name}-{recording.encounter.encounter_name}-{recording.encounter.location}-{filespace_handler.format_date_for_filespace(recording.start_time)}_ctr_files.zip"
        file_paths = [ctr_file.get_full_absolute_path() for ctr_file in ctr_files]
        response = utils.download_files(ctr_files, file_names, zip_filename)
        
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
    with database_handler.get_session() as session:
        selections = database_handler.create_system_time_request(session, models.Selection, {"recording_id":recording_id})
        recording = database_handler.create_system_time_request(session, models.Recording, {"id":recording_id}, one_result=True)
        selection_files = [selection.selection_file for selection in selections if selection.selection_file is not None]
        file_names = [selection.generate_selection_file_name() for selection in selections if selection.selection_file is not None]
        zip_filename = f"{recording.encounter.species.species_name}-{recording.encounter.encounter_name}-{recording.encounter.location}-{filespace_handler.format_date_for_filespace(recording.start_time)}_selection_files.zip"
        file_paths = [selection_file.get_full_absolute_path() for selection_file in selection_files]
        response = utils.download_files(selection_files, file_names, zip_filename)
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
    with database_handler.get_session() as session:
        selections = database_handler.create_system_time_request(session, models.Selection, {"recording_id":recording_id})
        recording = database_handler.create_system_time_request(session, models.Recording, {"id":recording_id}, one_result=True)
        contour_files = [selection.contour_file for selection in selections if selection.contour_file is not None]
        file_names = [selection.generate_contour_file_name() for selection in selections if selection.contour_file is not None]
        zip_filename = f"{recording.encounter.species.species_name()}-{recording.encounter.encounter_name}-{recording.encounter.location}-{filespace_handler.format_date_for_filespace(recording.start_time)}_contour_files.zip"
        file_paths = [contour_file.get_full_absolute_path() for contour_file in contour_files]
        response = utils.download_files(contour_files, file_names, zip_filename)
        return response
    
@routes_recording.route('/recording/<recording_id>/download-recording-file', methods=['GET'])
@login_required
def download_recording_file(recording_id):
    with database_handler.get_session() as session:
        recording = database_handler.create_system_time_request(session, models.Recording, {"id":recording_id}, one_result=True)
        return utils.download_file(recording.recording_file, filename = recording.recording_file_name)

    
@routes_recording.route('/recording/<recording_id>/mark_as_complete', methods=['GET'])
@database_handler.require_live_session
@login_required
@database_handler.exclude_role_3
@database_handler.exclude_role_4
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
    with database_handler.get_session() as session:
        recording = session.query(models.Recording).filter_by(id=recording_id).first()
        recording.status = "Reviewed"
        session.commit()
        return redirect(url_for('recording.recording_view', recording_id=recording_id))

@routes_recording.route('/recording/<recording_id>/mark_as_on_hold', methods=['GET'])
@database_handler.require_live_session
@login_required
@database_handler.exclude_role_3
@database_handler.exclude_role_4
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
    with database_handler.get_session() as session:
        recording = session.query(models.Recording).filter_by(id=recording_id).first()
        recording.status = "On Hold"
        session.commit()
        return redirect(url_for('recording.recording_view', recording_id=recording_id))