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
from .routes_recording import check_editable

routes_selection = Blueprint('selection', __name__)

def insert_or_update_selection(session, selection_number: str, file, recording_id: str, selection:models.Selection=None) -> models.Selection:
    """ A helper function to insert or update a selection in the database. If the selection
    already exists, it will be updated. If the selection does not exist, it will be inserted.
    This function will also create the selection file and insert it into the database. If the
    selection file does not fulfil validity requirements, the entire transaction is cancelled.

    Args:
        session (Session): The current database session.
        selection_number (str): The number identifying the selection.
        file (FileStorage): The file to be associated with the selection.
        recording_id (str): The ID of the recording to which the selection belongs.
        selection_id (str, optional): The ID of the selection to update. If None, a new selection will be created.

    Raises:
        exception_handler.WarningException: If a selection file already exists for the given selection.
        SQLAlchemyError: If a database error occurs during the transaction.

    Returns:
        models.Selection: The selection object that was inserted or updated.
    """
    
    # Create a new selection object if one was not given
    if selection is None:
        selection = models.Selection()
        selection.recording_id = recording_id
        session.add(selection)
        selection.set_selection_number(selection_number)
        # This flush is crucial for generate_relative_path() and generate_selection_file_name() used below
        session.flush()
    # Raise an exception if a selection file already exists
    if selection.selection_file_id is not None:
        raise exception_handler.WarningException(f"Selection file for {selection.get_unique_name()} already exists.")
    new_file = models.File()
    session.add(new_file)

    new_file.insert_path_and_filename(session, file, selection.generate_relative_path(), selection.generate_selection_file_name())

    # Try to assign the new selection file to the selection
    # The method Selection.set_selection_file() will throw an exception if the selection file is not valid
    try:
        selection.set_selection_file(new_file)
    except Exception as e:
        new_file.rollback(session)
        raise e
    session.flush()
    return selection

def generate_ctr_file(session, selection_id):
    """A method to generate a CTR file (based on a contour file in `selection`). This method
    will handle the generation of the CTR file, as well as the saving of the contour file.

    Raises:
        exception_handler.WarningException: if a non-critical error occurs
        Exception: if an unexpected error occurs
        sqlalchemy.exc.SQLAlchemyError: if a database error occurs

    Returns:
        None
    """
    selection = session.query(models.Selection).filter_by(id=selection_id).first()
    if not selection.contour_file: return
    selection.calculate_and_save_ctr_data()
    # Reflect this change in the database
    file_obj = models.File()
    file_obj.insert_path_and_filename_file_already_in_place(session, selection.generate_relative_path(),selection.generate_ctr_file_name().split(".")[0], "ctr")
    session.add(file_obj)
    selection.ctr_file = file_obj
    session.commit()

@routes_selection.route('/selection/<selection_id>/regenerate-contour-calculations', methods=['POST'])
@login_required
@database_handler.exclude_role_4
@database_handler.require_live_session
def regenerate_contour_calculations(selection_id):
    """
    This route uses `response_handler.JSONResponse` to return a JSON response. Please follow the protocol presented by
    this object in the client code. More information can be found in `response_handler.py`.

    Route to regenerate the contour calculations for a selection. This involved both regenerating the CTR file and 
    recalculating the contour statistics of the selection. Both these operations require a contour file to be present
    in the selection. Failure to have a contour file present will cause an error to be added to the response. Successful
    completion of the recalculation will cause a redirect to the referrer of the request in the response.

    Args:
        selection_id (_type_): the UUID of the selection for which the CTR file and contour statistics are to be recalculated

    Returns:
        flask.Response: a JSON response
    """
    response = response_handler.JSONResponse()
    with database_handler.get_session() as session:
        try:
            selection = session.query(models.Selection).filter_by(id=selection_id).first()
            # Check if the user has permission to edit the selection
            recording = session.query(models.Recording).filter_by(id=selection.recording_id).first()
            check_editable(recording)
            generate_ctr_file(session, selection_id)
            selection.recalculate_contour_statistics()
            session.commit()
            flash(f"Contour statistics for {selection.get_unique_name()} have been recalculated.", "success")
            response.set_redirect(request.referrer)
        except (Exception, SQLAlchemyError) as e:
            # A ValueError from Selection.recalculate_contour_statistics() occurs when the contour file is missing
            if type(e) == ValueError: e = exception_handler.WarningException(e.args[0])
            response.add_error(exception_handler.handle_exception(exception=e, prefix="Error refreshing contour statistics", session=session, show_flash=False))
    return response.to_json()

@routes_selection.route('/contour_file_delete/<selection_id>', methods=["GET", "POST"])
@database_handler.require_live_session
@login_required
@database_handler.exclude_role_4
def contour_file_delete(selection_id: str):
    """
    This function deletes a contour file associated with a selection
    and updates the traced status of the selection.
    
    :param selection_id: the id of the selection to be deleted
    :return: redirects to the recording view of the recording associated with the selection.
    """
    response = response_handler.JSONResponse()
    with database_handler.get_session() as session:
        try:
            selection_obj = session.query(models.Selection).filter_by(id=selection_id).first()
            if selection_obj:
                recording_obj = session.query(models.Recording).filter_by(id=selection_obj.recording_id).first()
                check_editable(recording_obj)
                selection_obj.delete_contour_file(False)
                session.flush()
                selection_obj.update_traced_status()
                session.commit()
                response.set_redirect(request.referrer)
            else:
                response.add_error(f"Unable to delete contour file due to internal error.")
        except (SQLAlchemyError,Exception) as e:
            response.add_error(exception_handler.handle_exception(exception=e, prefix="Error deleting contour file", session=session, show_flash=False))
        return response.to_json()

def insert_or_update_contour(session, selection: models.Selection, contour_file):
    """
    Inserts or updates a contour file associated with a selection and calculates all necessary
    contour statistics.

    :param session: the current session object
    :param selection: the selection object to be updated
    :param contour_file: the contour file to be inserted or updated (the datatype is FileStorage of the Flask werkzeug framework)
    :return: the updated selection object
    """
    session.flush()
    # Create a new File object for the contour file
    if selection.contour_file is not None:
        raise exception_handler.WarningException(f"Contour file for selection {selection.selection_number} already exists.")
    new_file = models.File()
    selection.contour_file = new_file
    new_file.insert_path_and_filename(session, contour_file, selection.generate_relative_path(), selection.generate_contour_file_name())
    session.add(new_file)
    session.flush()
    # Attribute the new contour file to the selection
    # and reset the traced status
    selection.update_traced_status()
    selection.recalculate_contour_statistics()
    return selection

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

    The selection number is extracted using 'sel_(\d+)' in the filename of the contour file.

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
        match = re.search(r'sel_(\d+)', filename)
        if match:
            # If no selection number is given, use the one extracted from the filename (if possible)
            if selection_number == None or selection_number.strip() == "":
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
        
        selection = session.query(models.Selection).filter(database_handler.db.text("selection_number = :selection_number and recording_id = :recording_id")).params(selection_number=selection_number, recording_id=recording_id).first()

        if selection:
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

    The selection number is extracted using 'sel_(\d+)' in the filename of the contour file.

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
    match = re.search(r'sel_(\d+)', filename)
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
            

    print(jsonify(id=selection_number,messages=messages,valid=valid))
    return jsonify(id=selection_number,messages=messages,valid=valid)

@routes_selection.route('/serve_plot/<selection_id>')
@login_required
@database_handler.require_live_session
def serve_plot(selection_id: str):
    """
    A function that serves a spectrogram plot of a selection.

    :param selection_id: the id of the selection
    :type selection_id: str
    :param fft_size: the FFT size to use for the spectrogram
    :type fft_size: int (HTTP argument), default None
    :param hop_size: the hop size to use for the spectrogram
    :type hop_size: int (HTTP argument), default None
    :return: a PNG image of the spectrogram
    """
    with database_handler.get_operation_lock() as operation_lock:
        fft_size = request.args.get('fft_size', type=int) if request.args.get('fft_size', type=int) else None
        hop_size = request.args.get('hop_size', type=int) if request.args.get('hop_size', type=int) else None
        with database_handler.get_session() as session:
            filespace_handler.clean_filespace_temp()
            selection = database_handler.create_system_time_request(session, models.Selection, {"id":selection_id}, one_result=True)
            temp_dir = tempfile.mkdtemp(dir=database_handler.get_tempdir())  # Use mkdtemp for manual cleanup
            update_permissions = True if current_user.role_id != 4 else False
            plot_file_path = selection.create_temp_plot(session, temp_dir, fft_size, hop_size, update_permissions=update_permissions)
        return send_file(plot_file_path, mimetype='image/png')


@routes_selection.route('/recording/<recording_id>/contour-insert', methods=['POST'])
@database_handler.require_live_session
@login_required
@database_handler.exclude_role_4
def contour_insert(recording_id):
    """
    Handles a POST request to upload multiple contour files for a given recording. The request
    must include a form field with the name 'files' that contains the files to be uploaded. The
    files should be of the type FileStorage from werkzeug. On completion the client side should
    refresh the page so that status flash messages are shown.

    :param recording_id: the id of the recording
    :type recording_id: str
    :return: a JSON response with a success message
    """
    response = response_handler.JSONResponse()

    with database_handler.get_session() as session:
        try:
            if 'file' in request.files and request.files['file'].filename != '':
                # Access the uploaded files
                file = request.files.get('file')
                id = request.form.get('id')

                # Insert or update the selection
                current_selection_object = session.query(models.Selection).filter(database_handler.db.text("selection_number = :selection_number and recording_id = :recording_id")).params(selection_number=id, recording_id=recording_id).first()
                if current_selection_object is not None:
                    insert_or_update_contour(session, current_selection_object, file)
                else:
                    response.add_error(f"Could not find corresponding selection with selection number {id}.")
                session.commit()
            else:
                response.add_error("Bad file in request.")
        except (Exception, SQLAlchemyError) as e:
            response.add_error(exception_handler.handle_exception(exception=e, session=session, show_flash=False))
        finally:
            return response.to_json()

@routes_selection.route('/recording/<recording_id>/selection-insert', methods=['POST'])
@database_handler.require_live_session
@login_required
@database_handler.exclude_role_4
def selection_insert(recording_id):
    """
    A route to insert a selection file into the filespace. In the event that a selection
    does not yet exist for a selection file, create a new selection in the database then
    add the selection file.

    Requires the following MANDATORY arguments in the HTTP request: 
    - last: 'true' or 'false' on whether this request is the last (set to 'true' if just uploading one selection file)
    - successCounter: the number of files that have been successfully uploaded
    - id: the selection number of the file to be added
    - file: the file to upload from the HTTP file browser

    :param recording_id: the id of the recording to add the selection to
    :type recording_id: str
    :return: a JSON response with a success message if the files are uploaded successfully
    """

    response = response_handler.JSONResponse()
    with database_handler.get_session() as session:
        try:
            recording = session.query(models.Recording).filter_by(id=recording_id).first()
            check_editable(recording)
            if 'file' in request.files and request.files['file'].filename != '':
                file = request.files.get('file')
                id = request.form.get('id')
                selection = session.query(models.Selection).filter(database_handler.db.text("selection_number = :selection_number and recording_id = :recording_id")).params(selection_number=id, recording_id=recording_id).first()
                if selection is not None: insert_or_update_selection(session,id, file, recording=recording, selection=selection)
                else: insert_or_update_selection(session,id, file, recording_id)
                session.commit()
            else:
                response.add_error(f"Bad file in request.")
        except (Exception,SQLAlchemyError) as e:
            response.add_error(exception_handler.handle_exception(exception=e, session=session,show_flash=False))
        # If the final selection was uploaded flash a success message
        # Otherwise add the counter to the response data
        return response.to_json()

@routes_selection.route('/selection/<selection_id>/download-ctr', methods=['GET'])
def download_ctr_file(selection_id):
    with database_handler.get_session() as session:
        selection = database_handler.create_system_time_request(session, models.Selection, {"id":selection_id}, one_result=True)
        return utils.download_file(selection.get_ctr_file(), selection.generate_ctr_file_name)

@routes_selection.route('/selection/<selection_id>/download-contour', methods=['GET'])
def download_contour_file(selection_id):
    with database_handler.get_session() as session:
        selection = database_handler.create_system_time_request(session, models.Selection, {"id":selection_id}, one_result=True)
        return utils.download_file(selection.get_contour_file(), selection.generate_contour_file_name)

@routes_selection.route('/selection/<selection_id>/download-selection', methods=['GET'])
def download_selection_file(selection_id):
    with database_handler.get_session() as session:
        selection = database_handler.create_system_time_request(session, models.Selection, {"id":selection_id}, one_result=True)
        return utils.download_file(selection.get_selection_file(), selection.generate_selection_file_name)

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

        selection_dict = {
            'freq_max': selection.freq_max,
            'freq_min': selection.freq_min,
            'duration': selection.duration,
            'freq_begin': selection.freq_begin,
            'freq_end': selection.freq_end,
            'freq_range': selection.freq_range,
            'dc_mean': selection.dc_mean,
            'dc_standarddeviation': selection.dc_standarddeviation,
            'freq_mean': selection.freq_mean,
            'freq_standarddeviation': selection.freq_standarddeviation,
            'freq_median': selection.freq_median,
            'freq_center': selection.freq_center,
            'freq_relbw': selection.freq_relbw,
            'freq_maxminratio': selection.freq_maxminratio,
            'freq_begendratio': selection.freq_begendratio,
            'freq_quarter1': selection.freq_quarter1,
            'freq_quarter2': selection.freq_quarter2,
            'freq_quarter3': selection.freq_quarter3,
            'freq_spread': selection.freq_spread,
            'dc_quarter1mean': selection.dc_quarter1mean,
            'dc_quarter2mean': selection.dc_quarter2mean,
            'dc_quarter3mean': selection.dc_quarter3mean,
            'dc_quarter4mean': selection.dc_quarter4mean,
            'freq_cofm': selection.freq_cofm,
            'freq_stepup': selection.freq_stepup,
            'freq_stepdown': selection.freq_stepdown,
            'freq_numsteps': selection.freq_numsteps,
            'freq_slopemean': selection.freq_slopemean,
            'freq_absslopemean': selection.freq_absslopemean,
            'freq_posslopemean': selection.freq_posslopemean,
            'freq_negslopemean': selection.freq_negslopemean,
            'freq_sloperatio': selection.freq_sloperatio,
            'freq_begsweep': selection.freq_begsweep,
            'freq_begup': selection.freq_begup,
            'freq_begdown': selection.freq_begdown,
            'freq_endsweep': selection.freq_endsweep,
            'freq_endup': selection.freq_endup,
            'freq_enddown': selection.freq_enddown,
            'num_sweepsupdown': selection.num_sweepsupdown,
            'num_sweepsdownup': selection.num_sweepsdownup,
            'num_sweepsupflat': selection.num_sweepsupflat,
            'num_sweepsdownflat': selection.num_sweepsdownflat,
            'num_sweepsflatup': selection.num_sweepsflatup,
            'num_sweepsflatdown': selection.num_sweepsflatdown,
            'freq_sweepuppercent': selection.freq_sweepuppercent,
            'freq_sweepdownpercent': selection.freq_sweepdownpercent,
            'freq_sweepflatpercent': selection.freq_sweepflatpercent,
            'num_inflections': selection.num_inflections,
            'inflection_maxdelta': selection.inflection_maxdelta,
            'inflection_mindelta': selection.inflection_mindelta,
            'inflection_maxmindelta': selection.inflection_maxmindelta,
            'inflection_meandelta': selection.inflection_meandelta,
            'inflection_standarddeviationdelta': selection.inflection_standarddeviationdelta,
            'inflection_mediandelta': selection.inflection_mediandelta,
            'inflection_duration': selection.inflection_duration,
            'step_duration': selection.step_duration,
            }
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
    print(request.data)
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
        except (Exception, SQLAlchemyError) as e:
            response.add_error(exception_handler.handle_exception(exception=e, prefix="Error updating selection", session=session, show_flash=False))
    return response.to_json()

import csv
from flask import Response
from io import StringIO

def write_contour_stats(selections, filename):
    """
    Write contour stats for a list of selections to a CSV file.

    :param selections: The list of Selection objects to write stats for
    :type selections: List[Selection]
    :param filename: The name of the CSV file to write to
    :type filename: str
    :return: A Response object with the CSV contents
    """
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Encounter','Location','Project','Recording','Species','SamplingRate','SELECTIONNUMBER','FREQMAX', 'FREQMIN', 'DURATION', 'FREQBEG', 'FREQEND', 'FREQRANGE', 'DCMEAN', 'DCSTDDEV', 'FREQMEAN', 'FREQSTDDEV', 'FREQMEDIAN', 'FREQCENTER', 'FREQRELBW', 'FREQMAXMINRATIO', 'FREQBEGENDRATIO', 'FREQQUARTER1', 'FREQQUARTER2', 'FREQQUARTER3', 'FREQSPREAD', 'DCQUARTER1MEAN', 'DCQUARTER2MEAN', 'DCQUARTER3MEAN', 'DCQUARTER4MEAN', 'FREQCOFM', 'FREQSTEPUP', 'FREQSTEPDOWN', 'FREQNUMSTEPS', 'FREQSLOPEMEAN', 'FREQABSSLOPEMEAN', 'FREQPOSSLOPEMEAN', 'FREQNEGSLOPEMEAN', 'FREQSLOPERATIO', 'FREQBEGSWEEP', 'FREQBEGUP', 'FREQBEGDWN', 'FREQENDSWEEP', 'FREQENDUP', 'FREQENDDWN', 'NUMSWEEPSUPDWN', 'NUMSWEEPSDWNUP', 'NUMSWEEPSUPFLAT', 'NUMSWEEPSDWNFLAT', 'NUMSWEEPSFLATUP', 'NUMSWEEPSFLATDWN', 'FREQSWEEPUPPERCENT', 'FREQSWEEPDWNPERCENT', 'FREQSWEEPFLATPERCENT', 'NUMINFLECTIONS', 'INFLMAXDELTA', 'INFLMINDELTA', 'INFLMAXMINDELTA', 'INFLMEANDELTA', 'INFLSTDDEVDELTA', 'INFLMEDIANDELTA', 'INFLDUR', 'STEPDUR'])

    for selection in selections:
        if selection.traced:
            writer.writerow(list(selection.get_rounded_value(x) for x in selection.generate_contour_stats_array()))
    
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
    """
    Deactivate selections in the database.

    Expects a JSON payload with a list of selection IDs under the key "selectionIds".
    Returns a JSON response with a message indicating success or failure.
    """
    response = response_handler.JSONResponse()
    with database_handler.get_session() as session:
        selection_ids = request.json.get('selection_ids', [])
        if not selection_ids:
            response.add_error('No selection IDs provided')
            return response.to_json()

        selections = session.query(models.Selection).filter(models.Selection.id.in_(selection_ids)).all()
        success_counter = 0
        for selection in selections:
            try:
                check_editable(selection.recording)
            except Exception as e:
                response.add_error(exception_handler.handle_exception(exception=e, session=session, show_flash=False))
                return response.to_json()
            try:
                selection.deactivate()
                success_counter += 1
            except Exception as e:
                response.add_error("Error deactivating selection " + str(selection.selection_number))
        session.commit()
        if success_counter > 0:
            flash(f'{success_counter} selections deactivated successfully', 'success')
            response.set_redirect(request.referrer)
        if success_counter == 0:
            response.add_error('No selections deactivated')
        return response.to_json()
    
@routes_selection.route('/selection/reactivate', methods=['POST'])
@database_handler.require_live_session
@login_required
@database_handler.exclude_role_4
def reactivate_selections():
    """
    reactivate selections in the database.

    Expects a JSON payload with a list of selection IDs under the key "selectionIds".
    Returns a JSON response with a message indicating success or failure.
    """
    response = response_handler.JSONResponse()
    with database_handler.get_session() as session:
        selection_ids = request.json.get('selection_ids', [])
        if not selection_ids:
            response.add_error('No selection IDs provided')
            return response.to_json()

        selections = session.query(models.Selection).filter(models.Selection.id.in_(selection_ids)).all()
        success_counter = 0
        for selection in selections:
            try:
                check_editable(selection.recording)
            except Exception as e:
                response.add_error(exception_handler.handle_exception(exception=e, session=session, show_flash=False))
                return response.to_json()
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