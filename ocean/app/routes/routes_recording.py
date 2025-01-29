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
from functools import wraps
import typing
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
from .. import transaction_handler

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

@routes_recording.route('/recording/<recording_id>/selection-table/refresh', methods=['POST'])
def selection_table_refresh(recording_id):
    """POST route to re-apply the uploaded selection table file to the recording. Response uses
    the `response_handler.JSONResponse()` protocol.
    
    Will also update the traced status of all selections in the recording based on the annotations
    in the selection table and the contour files uploaded. If the update was successful or there
    exists no selection table in the recording, the response will redirect to the referrer. If
    any errors occur the response will include an error message with no redirect.

    If the recording is marked as Reviewed and the user is not an admin, an error is logged.
    """
    with response_handler.json_response_context() as response:
        with transaction_handler.atomic() as session:
            recording = session.query(models.Recording).filter_by(id=recording_id).first()
            check_editable(recording)
            new_selections = recording.selection_table_apply()
            for new_selection in new_selections:
                session.add(new_selection)
            recording.update_selection_traced_status()
            flash_message = f'Updated selection table for {recording.unique_name}.'
        flash(flash_message, 'success')
        response.set_redirect(request.referrer)
    return response.to_json()

@routes_recording.route('/recording/<recording_id>/selection-table/insert', methods=['POST'])
@database_handler.require_live_session
@database_handler.exclude_role_4
@login_required
def selection_table_insert(recording_id):
    check_editable_recording(recording_id)       
    with response_handler.json_response_context() as response:
        with transaction_handler.atomic_with_filespace() as transaction:
            session = transaction.session
            selection_table_file = transaction.create_tracked_file()
            recording = session.query(models.Recording).filter_by(id=recording_id).first()
            if 'selection-table-file' in request.files and request.files['selection-table-file'].filename != '':
                selection_table_file.insert(request.files['selection-table-file'], recording.relative_directory, recording.selection_table_file_name)
                new_selections = recording.selection_table_file_insert(selection_table_file)
                for new_selection in new_selections:
                    session.add(new_selection)
            else: raise exception_handler.WarningException("The form did not send a selection table file.")
        flash("Selection table uploaded successfully", "success")
        response.set_redirect(request.referrer)
    return response.to_json()

@routes_recording.route('/export-selection-table/<recording_id>/<export_format>', methods=['GET'])
@login_required
def selection_table_export(recording_id: str, export_format: typing.Literal["csv", "txt"]):
    
    with database_handler.get_session() as session:
        try:
            recording = database_handler.create_system_time_request(session, models.Recording, {"id":recording_id}, one_result=True)
            return recording.selection_table_export(export_format)
        except Exception as e:
            exception_handler.handle_exception(exception=e, prefix="Error exporting selection table", session=session)
            return redirect(request.referrer)

@routes_recording.route('/recording/<recording_id>/selection-table/delete', methods=['DELETE','POST'])
@database_handler.require_live_session
@database_handler.exclude_role_4
@login_required
def selection_table_delete(recording_id: str):
    from .. import transaction_handler
    response = response_handler.JSONResponse()
    with response_handler.json_response_context() as response:
        with transaction_handler.atomic_with_filespace() as (transaction_proxy):
            session = transaction_proxy.session
            recording = session.query(models.Recording).filter_by(id=recording_id).first()
            transaction_proxy.track_file(recording.selection_table_file)
            recording.selection_table_file_delete()
            recording.update_selection_traced_status()
            filespace_handler.action_to_be_deleted(session)
            response.set_redirect(request.referrer)
            flash(f'Deleted selection table from {recording.unique_name}.', 'success')
            
    return response.to_json()      

def recording_file_insert_helper(recording, transaction, form):
    if 'upload_recording_file_id' in form and 'upload_recording_file_name' in form and form['upload_recording_file_id'] and form['upload_recording_file_name']:
        recording_file = transaction.create_tracked_file()
        recording_file.insert(file=filespace_handler.get_complete_temporary_file(form['upload_recording_file_id'], form['upload_recording_file_name']), directory=recording.relative_directory, filename=recording.recording_file_name)
        recording.recording_file_insert(recording_file)

@routes_recording.route('/encounter/<encounter_id>/recording/insert', methods=['POST'])
@database_handler.require_live_session
@database_handler.exclude_role_3
@database_handler.exclude_role_4
@login_required
def recording_insert(encounter_id: str):
    with response_handler.json_response_context() as response:
        with transaction_handler.atomic_with_filespace() as transaction:
            session = transaction.session
            encounter = session.query(models.Encounter).filter_by(id=encounter_id).first()
            recording = models.Recording(encounter = encounter)
            success_message = f'Inserted {recording.unique_name}.'
            session.add(recording)
            recording.insert(request.form)
            recording_file_insert_helper(recording, transaction, request.form)
        flash(success_message)
        response.set_redirect(url_for('encounter.encounter_view', encounter_id=encounter_id))
    return response.to_json()

@routes_recording.route('/recording/<recording_id>/update', methods=['POST'])
@database_handler.require_live_session
@database_handler.exclude_role_3
@database_handler.exclude_role_4
@login_required
def recording_update(recording_id: str) -> Response:
    with response_handler.json_response_context() as response:
        with transaction_handler.atomic_with_filespace() as transaction:
            session = transaction.session
            recording = session.query(models.Recording).with_for_update().filter_by(id=recording_id).first()
            if not recording: raise exception_handler.DoesNotExistError("recording")
            check_editable(recording)
            recording.update(request.form)
            session.add(recording)
            recording_file_insert_helper(recording, transaction, request.form)
            flash(f'Updated {recording.unique_name}.', 'success')
        response.set_redirect(request.referrer)
    return response.to_json()

@routes_recording.route('/recording/<recording_id>/view', methods=['GET'])
@login_required
def recording_view(recording_id: str) -> Response:
    with database_handler.get_session() as session:
        recording = database_handler.create_system_time_request(session, models.Recording, {"id":recording_id}, one_result=True)
        if not recording: raise exception_handler.DoesNotExistError("recording")
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

def assignment_flag_change_helper(completed_flag):
    """Helper method for `assignment_flag_as_complete` and `assignment_flag_as_incomplete`"""
    response = response_handler.JSONResponse()
    with database_handler.get_session() as session:
        try:
            form = utils.parse_form(request.form, schema={"recording_id":True, "user_id": False})
            recording_id = form['recording_id']
            # Only allow the user to update someone else's assignment if they have adequate permissions.
            # Users without permission to update someone else's assignment usually will not include `user_id` in the form
            if 'user_id' not in form:
                user_id = current_user.id
            elif 'user_id' in form and current_user.role_id >= 3: raise exception_handler.WarningException('You cannot unflag an assignment for another user.')
            else: user_id = form['user_id']
            assignment = session.query(models.Assignment).filter_by(user_id=user_id).filter_by(recording_id=recording_id).first()
            if not assignment: raise exception_handler.Exception(f"No assignment with user_id '{user_id}' and recording_id '{recording_id}'")
            assignment.completed_flag = completed_flag
            session.commit()
            status_changed = assignment.recording.update_status(session)
            session.commit()
            response.set_redirect(request.referrer)
            flash(f"Assignment {assignment.unique_name} set as {'complete' if completed_flag else 'incomplete'}.", category="success")
            if status_changed: flash(f"Recording status updated to {assignment.recording.status}.", category="success")
        except Exception as e:
            response.add_error(exception_handler.handle_exception(exception=e, prefix="Error updating assignment", session=session, show_flash=False))
    return response.to_json()

@routes_recording.route('/recording/flag-as-completed-for-user', methods=['POST'])
@database_handler.require_live_session
@database_handler.exclude_role_4
@login_required
def assignment_flag_as_complete():
    """POST route to mark an assignment as complete. The response follows the protocol
    of `response_handler.JSONResponse`.

    Requires `recording_id` in the form data. If a `user_id` is provided the assignment
    will be of the `user_id` and `recording_id`. If a `user_id` is not provided the
    assignment will be of the current logged in user id and `recording_id`. If the
    combination of `user_id` and `recording_id` do not exist, or they do exist but
    an error occurs, the error will be added to the response.
    
    This route will also update the overall recording status.
    """
    return assignment_flag_change_helper(True)

@routes_recording.route('/recording/unflag-as-completed-for-user', methods=['POST'])
@database_handler.require_live_session
@database_handler.exclude_role_4
@login_required
def assignment_flag_as_incomplete():
    """POST route to mark an assignment as incomplete. The response follows the protocol
    of `response_handler.JSONResponse`.

    Requires `recording_id` in the form data. If a `user_id` is provided the assignment
    will be of the `user_id` and `recording_id`. If a `user_id` is not provided the
    assignment will be of the current logged in user id and `recording_id`. If the
    combination of `user_id` and `recording_id` do not exist, or they do exist but
    an error occurs, the error will be added to the response.
    
    This route will also update the overall recording status.
    """
    return assignment_flag_change_helper(False)

@routes_recording.route('/recording/assignment-delete', methods=['POST'])
@database_handler.require_live_session
@database_handler.exclude_role_4
@database_handler.exclude_role_3
@login_required
def assignment_delete():
    response = response_handler.JSONResponse()
    with database_handler.get_session() as session:
        try:
            form = utils.parse_form(request.form, schema={"recording_id":True, "user_id":True})
            assignment = session.query(models.Assignment).filter_by(user_id=form['user_id']).filter_by(recording_id=form['recording_id']).first()
            unique_name = assignment.unique_name
            if not assignment: raise Exception(f"No assignment with user_id '{form['user_id']}' and recording_id '{form['recording_id']}'")
            session.delete(assignment)
            session.commit()
            flash(f"Assignment {unique_name} deleted.", category="success")
            response.set_redirect(request.referrer)
        except Exception as e:
            response.add_error(exception_handler.handle_exception(exception=e, prefix="Error deleting assignment", session=session, show_flash=False))
    return response.to_json()


@routes_recording.route('/recording/<recording_id>/delete', methods=['POST'])
@database_handler.require_live_session
@database_handler.exclude_role_3
@database_handler.exclude_role_4
@login_required
def recording_delete(recording_id):
    with response_handler.json_response_context() as response:
        with transaction_handler.atomic() as session:
            recording = session.query(models.Recording).filter_by(id=recording_id).first()
            if recording:
                encounter_id = recording.encounter_id
                unique_name = recording.unique_name
                recording.delete(session)
                flash(f'Deleted {unique_name}.', 'success')
            response.set_redirect(url_for("encounter.encounter_view", encounter_id=encounter_id))
    return response.to_json()

@routes_recording.route('/recording/<recording_id>/recording-file-delete',methods=['POST'])
@database_handler.require_live_session
@database_handler.exclude_role_3
@database_handler.exclude_role_4
@login_required
def recording_file_delete(recording_id):
    with response_handler.json_response_context() as response:
        with transaction_handler.atomic() as session:
            recording = session.query(models.Recording).filter_by(id=recording_id).first()
            recording.recording_file_delete()
            session.commit()
            flash(f'Deleted recording file from {recording.unique_name}.', 'success')
            response.set_redirect(request.referrer)
    return response.to_json()

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
    with response_handler.json_response_context() as response:
        with transaction_handler.atomic_with_filespace() as transaction_proxy:
            session = transaction_proxy.session
            data = request.get_json()
            selection_ids = data.get('selectionIds', [])
            if selection_ids == None or len(selection_ids) == 0: raise exception_handler.WarningException("No selections selected for deletion.")
            selections = session.query(models.Selection).filter(models.Selection.id.in_(selection_ids)).all()
            for selection in selections:
                check_editable(selection.recording)
                selection._delete_children(session)
            response.set_redirect(request.referrer)
            flash(f"Deleted {len(selection_ids)} selections.", category="success")
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
        date = utils.parse_date(filename)
        if not date:
            response.add_error('No date found in filename.')
        else:
            response.add_message('Date found in filename.')
        response.data['date'] = date
    except (Exception) as e:
        response.add_error(exception_handler.handle_exception(exception=e, session=None, show_flash=False))
    return response.to_json()

@routes_recording.route('/assign_recording', methods=['POST'])
@database_handler.require_live_session
@database_handler.exclude_role_3
@database_handler.exclude_role_4
@login_required
def assign_recording():
    """POST route to assign a recording to a user. Requires `user_id` and `recording_id` to be passed as
    arguments in the request. Returns a JSON response following the `response_handler.JSONResponse` protocol.
    (redirect on success, error message(s) on failure)."""

    response = response_handler.JSONResponse()
    response.set_redirect(request.referrer)
    with database_handler.get_session() as session:
        try:
            assignment = models.Assignment()
            assignment.insert(request.get_json())
            session.add(assignment)
            session.commit()
            flash(f'Assigned {assignment.recording.unique_name} to {assignment.user.unique_name}.', 'success')
            changed = assignment.recording.update_status(session)
            session.commit()
            if changed: flash(f'Updated status to {assignment.recording.status}.', 'success')
        except Exception as e:
            exception_handler.handle_exception(exception=e, session=session, show_flash=False)
    return response.to_json()

@routes_recording.route('/unassign_recording', methods=['GET'])
@database_handler.require_live_session
@database_handler.exclude_role_3
@database_handler.exclude_role_4
@login_required
def unassign_recording():
    """POST route to unassign a recording from a user. Requires `user_id` and `recording_id` to be passed as
    arguments in the request. Returns a JSON response following the `response_handler.JSONResponse` protocol.
    (redirect on success, error messages(s) on failure)."""
    
    response = response_handler.JSONResponse()
    with database_handler.get_session() as session:
        try:
            user_id = utils.extract_args('user_id')
            recording_id = utils.extract_args('recording_id')
            recording = session.query(models.Recording).filter_by(id=recording_id).first()
            assignment = session.query(models.Assignment).filter_by(user_id=user_id).filter_by(recording_id=recording_id).first()
            session.delete(assignment)
            session.flush()
            recording.update_status(session)
            session.commit()
            response.set_redirect(response.referrer)
        except Exception as e:
            response.add_error(exception_handler.handle_exception(exception=e, session=session, show_flash=False))
    return response.to_json()



@routes_recording.route('/recording/<recording_id>/recalculate-contour-statistics', methods=['POST'])
@login_required
@database_handler.exclude_role_4
@database_handler.require_live_session
def calculate_contour_statistics_for_recording(recording_id: str):
    with response_handler.json_response_context() as response:
        with transaction_handler.atomic_with_filespace() as transaction_proxy:
            session = transaction_proxy.session
            recording = session.query(models.Recording).filter_by(id=recording_id).first()
            check_editable(recording)
            count = 0
            for selection in recording.selections:
                if selection.contour_file: selection.ctr_file_generate(transaction_proxy.create_tracked_file())
                selection.contour_statistics_calculate()
                if selection.contour_file: count += 1
        response.add_message(f"{count} contour statistic(s) and CTR file(s) were regenerated.")
    return response.to_json()
    

@routes_recording.route('/recording/<recording_id>/download-ctr-files', methods=['GET'])
@login_required
def download_ctr_files(recording_id):
    with database_handler.get_session() as session:
        recording = database_handler.create_system_time_request(session, models.Recording, {"id":recording_id}, one_result=True)
        selections = database_handler.create_system_time_request(session, models.Selection, {"recording_id":recording_id})
        ctr_files = [selection.ctr_file for selection in selections if selection.ctr_file is not None]
        file_names = [selection.ctr_file_name for selection in selections if selection.ctr_file is not None]
        zip_filename = f"{recording.encounter.species.scientific_name}-{recording.encounter.encounter_name}-{recording.encounter.location}-{filespace_handler.format_date_for_filespace(recording.start_time)}_ctr_files.zip"
        file_paths = [ctr_file._path_with_root for ctr_file in ctr_files]
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
        file_names = [selection.selection_file_name for selection in selections if selection.selection_file is not None]
        zip_filename = f"{recording.encounter.species.scientific_name}-{recording.encounter.encounter_name}-{recording.encounter.location}-{filespace_handler.format_date_for_filespace(recording.start_time)}_selection_files.zip"
        file_paths = [selection_file._path_with_root for selection_file in selection_files]
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
        file_names = [selection.contour_file_name for selection in selections if selection.contour_file is not None]
        zip_filename = f"{recording.encounter.species.scientific_name}-{recording.encounter.encounter_name}-{recording.encounter.location}-{filespace_handler.format_date_for_filespace(recording.start_time)}_contour_files.zip"
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