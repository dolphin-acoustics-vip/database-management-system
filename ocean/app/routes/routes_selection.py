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

# Standard library imports
from functools import wraps
import os
import re
import tempfile

# Third-party imports
from flask import Blueprint, flash, jsonify, redirect,render_template,request, send_file,session, url_for, send_from_directory
from sqlalchemy.exc import SQLAlchemyError
from flask_login import login_required, current_user

# Location application imports
from .. import database_handler
from .. import models
from .. import exception_handler
from .. import utils
from .. import filespace_handler
from .. import response_handler
from .. import transaction_handler
from .routes_recording import check_editable

routes_selection = Blueprint('selection', __name__)

@routes_selection.route('/selection/<selection_id>/regenerate-contour-calculations', methods=['POST'])
@login_required
@database_handler.exclude_role_4
@database_handler.require_live_session
def calculate_contour_statistics(selection_id):
    with response_handler.json_response_context() as response:
        with transaction_handler.atomic_with_filespace() as transaction:
            session = transaction.session
            selection = session.query(models.Selection).filter_by(id=selection_id).first()
            recording = session.query(models.Recording).filter_by(id=selection.recording_id).first()
            check_editable(recording)
            selection.ctr_file_generate(transaction.create_tracked_file())
            selection.contour_statistics_calculate()
            flash(f"Contour statistics for {selection.unique_name} have been recalculated.", "success")
            response.set_redirect(request.referrer)
    return response.to_json()

@routes_selection.route('/contour_file_delete/<selection_id>', methods=["POST"])
@database_handler.require_live_session
@login_required
@database_handler.exclude_role_4
def contour_file_delete(selection_id: str):
    with response_handler.json_response_context() as response:
        with transaction_handler.atomic() as session:
            selection = session.query(models.Selection).filter_by(id=selection_id).first()
            if not selection: raise exception_handler.WarningException("Unable to delete contour file due to internal error.")
            recording = session.query(models.Recording).filter_by(id=selection.recording_id).first()
            check_editable(recording)
            selection.contour_file_delete()
            flash(f"Deleted contour file from {selection.unique_name}.", "success")
            response.set_redirect(request.referrer)
    return response.to_json()

@routes_selection.route('/process_contour', methods=["GET"])
@database_handler.require_live_session
@login_required
@database_handler.exclude_role_4
def process_contour():
    """
    A function that processes the filename of a contour file to ensure that it is valid.
    This is completed in the pre-processing stage before a contour is uploaded to the 
    database. If no selection number has been given, one is automatically extracted from
    the filename of the contour file being processed. 

    The selection number is extracted using 'sel[-_](\\d+)' in the filename of the contour file.

    :param recording_id: the id of the recording
    :type recording_id: str (HTTP argument)
    :param filename: the name of the contour file
    :type filename: str (HTTP argument)
    :param selection_number: the selection number associated with the contour file
    :type selection_number: str (HTTP argument), default None
    :return: a JSON object with the selection number, a list of messages and a boolean indicating whether the file is valid or not
    """
    recording_id = request.args.get('recording_id')
    filename = request.args.get('filename')
    selection_number = request.args.get('id')
    valid = True
    messages = []

    extension = filename.split('.')[-1]
    if extension != "csv":
        messages.append("<span style='color: red;'>Error: must be a CSV file.</span>")
        valid = False
    with database_handler.get_session() as session:
        # Extract the selection number from the filename using regular expression
        match = re.search(r'sel[-_](\d+)', filename)
        if match:
            # If no selection number is given, use the one extracted from the filename (if possible)
            if selection_number == None or selection_number.strip() == "":
                selection_number = match.group(1).lstrip('0')  # Remove leading zeros
                messages.append("Selection number: " + selection_number + ".")
                selection = session.query(models.Selection).filter_by(recording_id=recording_id).filter_by(selection_number=selection_number).first()
            else:
                if selection_number == match.group(1).lstrip('0'):
                    messages.append("Selection number: " + selection_number + ".")
                else:
                    messages.append("Selection number: " + selection_number + ".")
                    messages.append("<span style='color: orange;'>Warning: selection number mismatch.</span>")
        elif not match and selection_number == None:
            messages.append("<span style='color: red;'>Error: invalid selection number.</span>")
            valid=False
        else:
            messages.append("Selection number: " + selection_number + ".")
        
        selection = session.query(models.Selection).filter(database_handler.db.text("selection_number = :selection_number and recording_id = :recording_id")).params(selection_number=selection_number, recording_id=recording_id).first()

        if selection:
            if selection.contour_file != None or selection.contour_file_id != None:
                messages.append("<span style='color: red;'>Error: contour file already exists.</span>")
                valid = False
            if selection.annotation == "N":
                messages.append("<span style='color: orange;'>Selection annotated 'N'. Double check.</span>")
            elif selection.annotation == None:
                messages.append("<span style='color: orange;'>Selection not annotated. Double check selection table.</span>")
        else:
            messages.append("<span style='color: red;'>Could not cross-reference selection number.</span>")
            valid = False
        
        # Check if the selection start time matches that of its recording
        recording = session.query(models.Recording).filter(database_handler.db.text("id = :recording_id")).params(recording_id=recording_id).first()
        date = utils.parse_date(filename)
        if not date:
            messages.append("<span style='color: orange;'>Warning: no start time.</span>")            
        elif not recording.start_time == date:
            messages.append("<span style='color: orange;'>Warning: start time mismatch.</span>")
            
    return jsonify(id=selection_number,messages=messages,valid=valid)

@routes_selection.route('/process_selection', methods=['GET'])
@database_handler.require_live_session
@login_required
@database_handler.exclude_role_4
def process_selection():
    """
    A function that processes the filename of a contour file to ensure that it is valid.
    This is completed in the pre-processing stage before a contour is uploaded to the 
    database. If no selection number has been given, one is automatically extracted from
    the filename of the contour file being processed. 

    The selection number is extracted using 'sel[-_](\\d+)' in the filename of the contour file.

    :param recording_id: the id of the recording
    :type recording_id: str (HTTP argument)
    :param filename: the name of the contour file
    :type filename: str (HTTP argument)
    :param selection_number: the selection number associated with the contour file
    :type selection_number: str (HTTP argument), default None
    :return: a JSON object with the selection number, a list of messages and a boolean indicating whether the file is valid or not {id: selection_number, messages: [], valid: boolean}
    """
    recording_id = request.args.get('recording_id')
    filename = request.args.get('filename')
    extension = filename.split('.')[-1]

    selection_number = request.args.get('id')
    valid = True
    messages=[]
    if extension != "wav":
        messages.append("<span style='color: red;'>Error: must be WAV file.</span>")
        valid = False
    
    # Prevent empty strings from causing issues in the future
    if str(selection_number).strip() == "":
        selection_number = None
        
    # Extract the selection number from the filename using regular expression
    match = re.search(r'sel[-_](\d+)', filename)
    if match:
        if selection_number == None:
            selection_number = match.group(1).lstrip('0')  # Remove leading zeros
            messages.append("Selection number: " + selection_number + ".")
        else:
            if selection_number == match.group(1).lstrip('0'):
                messages.append("Selection number: " + selection_number + ".")
            else:
                messages.append("Selection number: " + selection_number + ".")
                messages.append("<span style='color: orange;'>Warning: selection number mismatch.</span>")
    elif not match and selection_number == None:
        messages.append("<span style='color: red;'>Error: invalid selection number.</span>")
        valid=False
    else:
        messages.append("Selection number: " + selection_number + ".")
    
    # Check if selection number is an integer
    if selection_number != None and selection_number != "":
        try:
            int(selection_number)
        except Exception:
            messages.append("<span style='color: red;'>Error: invalid selection number.</span>")
            valid=False
    
    # Check if selection number already exists
    with database_handler.get_session() as session:
        if selection_number != None:
            selection_number_exists = session.query(models.Selection).filter(database_handler.db.text("selection_number = :selection_number and recording_id = :recording_id")).params(selection_number=selection_number, recording_id=recording_id).first()
            if selection_number_exists:
                if selection_number_exists.selection_file_id is not None:
                    messages.append("<span style='color: red;'>Error: selection number already exists.</span>")
                    valid=False

        # Check if the selection start time matches that of its recording
        recording = session.query(models.Recording).filter(database_handler.db.text("id = :recording_id")).params(recording_id=recording_id).first()
        date = utils.parse_date(filename)
        if not date:
            messages.append("<span style='color: orange;'>Warning: no start time.</span>")            
        elif not recording.start_time == date:
            messages.append("<span style='color: orange;'>Warning: start time mismatch.</span>")
            
    return jsonify(id=selection_number,messages=messages,valid=valid)

@routes_selection.route('/serve-plot/<selection_id>')
@login_required
def serve_plot(selection_id: str):
    with database_handler.get_session() as session:
        filespace_handler.clean_filespace_temp()
        selection = database_handler.create_system_time_request(session, models.Selection, {"id":selection_id}, one_result=True)
        plot_bytestream = selection.create_temp_plot()
        response = Response(plot_bytestream, mimetype='image/png')
        response.headers['Content-Disposition'] = f'attachment; filename="{selection.plot_file_name}"'
        return response

@routes_selection.route('/recording/<recording_id>/contour-insert', methods=['POST'])
@database_handler.require_live_session
@login_required
@database_handler.exclude_role_4
def contour_file_insert(recording_id):
    with response_handler.json_response_context() as response:
        with transaction_handler.atomic_with_filespace() as transaction:
            session = transaction.session
            if 'file' in request.files and request.files['file'].filename != '':
                contour_file = transaction.create_tracked_file()
                ctr_file = transaction.create_tracked_file()
                file_stream = request.files.get('file')
                selection_number = request.form.get('selection_number')
                selection = session.query(models.Selection).filter(database_handler.db.text("selection_number = :selection_number and recording_id = :recording_id")).params(selection_number=selection_number, recording_id=recording_id).first()
                if not selection: raise exception_handler.WarningException(f"Could not find corresponding selection with selection number {selection_number}.")
                contour_file.insert(file_stream, selection.relative_directory, selection.contour_file_name)
                selection.contour_file_insert(contour_file = contour_file, ctr_file = ctr_file)
            else:
                raise exception_handler.WarningException("No contour file provided.")
    return response.to_json()


@routes_selection.route('/recording/<recording_id>/selection-insert', methods=['POST'])
@database_handler.require_live_session
@database_handler.exclude_role_4
@login_required
def selection_file_insert(recording_id):
    with response_handler.json_response_context() as response:
        with transaction_handler.atomic_with_filespace() as transaction:
            session = transaction.session
            recording = session.query(models.Recording).filter_by(id=recording_id).first()
            check_editable(recording)
            selection_number = request.form.get('selection_number')
            # Check if selection number already exists
            selection = session.query(models.Selection).filter(database_handler.db.text("selection_number = :selection_number and recording_id = :recording_id")).params(selection_number=selection_number, recording_id=recording_id).first()
            if not selection:
                selection = models.Selection(recording = recording)
                selection.insert(request.form)
                session.add(selection)
            # Add the selection file to the selection
            if 'file' in request.files and request.files['file'].filename != '':
                selection_file = transaction.create_tracked_file()
                selection_file.insert(request.files['file'], selection.relative_directory, selection.selection_file_name)
                selection.selection_file_insert(file = selection_file)
            else: raise exception_handler.WarningException(f"Bad file in request.")
    return response.to_json()

@routes_selection.route('/selection/<selection_id>/download-ctr', methods=['GET'])
def download_ctr_file(selection_id):
    with database_handler.get_session() as session:
        selection = database_handler.create_system_time_request(session, models.Selection, {"id":selection_id}, one_result=True)
        return utils.download_BytesIO(selection.generate_ctr_file(), selection.ctr_file_name)

@routes_selection.route('/selection/<selection_id>/download-contour', methods=['GET'])
def download_contour_file(selection_id):
    with database_handler.get_session() as session:
        selection = database_handler.create_system_time_request(session, models.Selection, {"id":selection_id}, one_result=True)
        return utils.download_file(selection.contour_file, selection.contour_file_name)

@routes_selection.route('/selection/<selection_id>/download-selection', methods=['GET'])
def download_selection_file(selection_id):
    with database_handler.get_session() as session:
        selection = database_handler.create_system_time_request(session, models.Selection, {"id":selection_id}, one_result=True)
        return utils.download_file(selection.selection_file, selection.selection_file_name)

@routes_selection.route('/selection/<selection_id>/view', methods=['GET'])
@login_required
def selection_view(selection_id):
    """
    Route to show the selection view page.

    :param selection_id: the id of the selection
    :type selection_id: str
    :return: a rendered HTML template
    """
    if request.args.get('snapshot_date'):
        database_handler.save_snapshot_date_to_session(request.args.get('snapshot_date'))
    with database_handler.get_session() as session:
        selection = database_handler.create_system_time_request(session, models.Selection, {"id":selection_id})[0]
        selection_history = database_handler.create_all_time_request(session, models.Selection, filters={"id":selection_id}, order_by="row_start")
        selection_dict = selection.get_contour_statistics_dict(use_headers=True)
        return render_template('selection/selection-view.html', selection=selection, selection_history=selection_history,selection_dict=selection_dict)

@routes_selection.route('/selection/confirm_no_file_upload', methods=['POST'])
@database_handler.require_live_session
@login_required
def confirm_no_file_upload():
    """
    Set traced to False for a selection. This is done when an annotation is Y or M but no contour file
    has been uploaded (i.e. the user has changed their mind on the annotation, and decided not to upload a contour).
    A record is made by setting the traced value of the selection to False.

    :param selection_id: the id of the selection
    :type selection_id: str
    :return: a JSON response with a success message if the selection is updated successfully
    """
    response = response_handler.JSONResponse()
    data = request.get_json()
    selection_id = data.get('selection_id', None)
    if not selection_id:
        response.add_error('No selection ID provided')
        return response.to_json()
    with database_handler.get_session() as session:
        try:
            selection = session.query(models.Selection).filter(models.Selection.id == selection_id).first()
            recording = session.query(models.Recording).filter(models.Recording.id == selection.recording_id).first()
            check_editable(recording)
            selection.traced = False
            session.commit()
        except Exception as e:
            response.add_error(exception_handler.handle_exception(exception=e, prefix="Error updating selection", session=session, show_flash=False))
    return response.to_json()

import csv
from flask import Response
from io import StringIO

def write_contour_stats(selections, filename):

    output = StringIO()
    writer = csv.writer(output)

    required_attrs = []

    header = ['Encounter','Location','Project','Recording','Species','SamplingRate','SELECTIONNUMBER']
    for k, v in models.Selection.get_contour_statistics_attrs().items():
        required_attrs.append(k)
        header.append(v[1])
    writer.writerow(header)
    for selection in selections:
        if selection.traced:
            row = [
                selection.recording.encounter.encounter_name,
                selection.recording.encounter.location,
                selection.recording.encounter.project,
                selection.recording.start_time,
                selection.recording.encounter.species.scientific_name,
                selection.sampling_rate,
                selection.selection_number
            ]
            for attr in required_attrs:
                row.append(getattr(selection, attr))
            writer.writerow(row)
    
    output.seek(0)
    return Response(output, mimetype='text/csv', headers={'Content-Disposition': f'attachment; filename="{filename}"'})
    
@routes_selection.route('/recording/<recording_id>/extract-contour-stats', methods=['GET'])
@database_handler.require_live_session
@login_required
def extract_contour_stats(recording_id):
    """
    Write contour stats for a list of selections to a CSV file.

    :param selections: The list of Selection objects to write stats for
    :type selections: List[Selection]
    :param filename: The name of the CSV file to write to
    :type filename: str
    :return: A Response object with the CSV contents
    """
    with database_handler.get_session() as session:
        selections = database_handler.create_system_time_request(session, models.Selection, {"recording_id":recording_id})
        recording = database_handler.create_system_time_request(session, models.Recording, {"id":recording_id}, one_result=True)
        return write_contour_stats(selections, filename=f"ContourStats-{recording.start_time_pretty}.csv")

@routes_selection.route('/encounter/<encounter_id>/extract-contour-stats-for-encounter', methods=['GET'])
def extract_contour_stats_for_encounter(encounter_id):
    """
    Write contour stats for all selections in an encounter to a CSV file.

    :param encounter_id: The id of the encounter to extract stats for
    :type encounter_id: str
    :return: A Response object with the CSV contents
    """
    with database_handler.get_session() as session:
        selections = []
        encounter = database_handler.create_system_time_request(session, models.Encounter, {"id":encounter_id}, one_result=True)
        recordings = database_handler.create_system_time_request(session, models.Recording, {"encounter_id":encounter_id})
        for recording in recordings:
            selections += database_handler.create_system_time_request(session, models.Selection, {"recording_id":recording.id})
        return write_contour_stats(selections, filename=f"ContourStats-{encounter.encounter_name}.csv")

@routes_selection.route('/selection/deactivate', methods=['POST'])
@database_handler.require_live_session
@login_required
@database_handler.exclude_role_4
def deactivate_selections():
    with response_handler.json_response_context() as response:
        with transaction_handler.atomic() as session:
            selection_ids = request.json.get('selection_ids', [])
            if not selection_ids: raise exception_handler.WarningException("No selections selected.")
            selections = session.query(models.Selection).filter(models.Selection.id.in_(selection_ids)).all()
            success_counter = 0
            for selection in selections:
                check_editable(selection.recording)
                try:
                    selection.deactivate()
                    success_counter += 1
                except Exception:
                    response.add_error("Error deactivating selection " + str(selection.selection_number))
        flash(f'{success_counter} selections deactivated successfully', 'success')
        response.set_redirect(request.referrer)
    return response.to_json()
    
@routes_selection.route('/selection/reactivate', methods=['POST'])
@database_handler.require_live_session
@login_required
@database_handler.exclude_role_4
def reactivate_selections():
    with response_handler.json_response_context() as response:
        with transaction_handler.atomic() as session:
            selection_ids = request.json.get('selection_ids', [])
            if not selection_ids: raise exception_handler.WarningException('No selections selected.')
            selections = session.query(models.Selection).filter(models.Selection.id.in_(selection_ids)).all()
            success_counter = 0
            for selection in selections:
                check_editable(selection.recording)
                try:
                    selection.reactivate()
                    success_counter += 1
                except Exception as e:
                    response.add_error("Error deactivating selection " + str(selection.selection_number))
            session.commit()
            if success_counter > 0:
                flash(f'{success_counter} selections reactivated successfully', 'success')
                response.set_redirect(request.referrer)
            if success_counter == 0:
                response.add_error('No selections reactivated')
    return response.to_json()