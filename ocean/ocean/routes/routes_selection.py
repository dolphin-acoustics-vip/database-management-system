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
import re
import tempfile

# Third-party imports
from flask import Blueprint, flash, jsonify, redirect,render_template,request, send_file,session, url_for, send_from_directory
from sqlalchemy.exc import SQLAlchemyError
from flask_login import login_required, current_user

# Location application imports
import ocean.database_handler as database_handler
import ocean.models as models
import ocean.exception_handler as exception_handler
import ocean.utils as utils

routes_selection = Blueprint('selection', __name__)

def insert_or_update_selection(session, selection_number: str, file, recording_id: str, selection_id:str=None) -> models.Selection:
    """
    A function to either insert a new Selection object or update an existing one in the database.
    
    :param session: The database session
    :param selection_number: the number of the selection
    :param file: the file to be associated with the selection (the datatype is FileStorage of the Flask werkzeug framework)
    :param recording_id: the id of the recording
    :param selection_id: the id of the selection to be updated (default is None if inserting a new selection)
    
    :return: the Selection object that was inserted or updated
    """

    # get Selection object if updating or make a new one if inserting
    if selection_id is not None:
        selection_obj = session.query(models.Selection).filter_by(id=selection_id).first()
    else:
        selection_obj = Selection()
        selection_obj.recording_id = recording_id
        session.add(selection_obj)
        selection_obj.set_selection_number(selection_number)
    session.flush()
    if selection_obj.selection_file_id is not None:
        raise exception_handler.WarningException(f"Selection file for {selection_obj.get_unique_name()} already exists.")
    selection_file = file
    selection_filename = selection_obj.generate_selection_filename()
    selection_relative_path = selection_obj.generate_relative_path()
    new_file = models.File()
    new_file.insert_path_and_filename(session, selection_file, selection_relative_path, selection_filename)
    selection_obj.set_selection_file(new_file)
    session.add(new_file)
    session.commit()
    return selection_obj


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
    with database_handler.get_session() as session:
        try:
            selection_obj = session.query(models.Selection).filter_by(id=selection_id).first()
            if selection_obj:
                selection_obj.delete_contour_file(False)
                session.flush()
                selection_obj.update_traced_status()
                session.commit()
            else:
                raise exception_handler.WarningException(f"Unable to delete contour file due to internal error.")
        except (SQLAlchemyError,Exception) as e:
            exception_handler.handle_exception(session, e, "Error deleting contour file")
        return redirect(request.referrer)

def insert_or_update_contour(session, selection: models.Selection, contour_file):
    """
    Inserts or updates a contour file associated with a selection and calculates all necessary
    contour statistics.

    :param session: the current session object
    :param selection: the selection object to be updated
    :param contour_file: the contour file to be inserted or updated (the datatype is FileStorage of the Flask werkzeug framework)
    :return: the updated selection object
    """
    # Create a new File object for the contour file
    session.flush()
    if selection.contour_file is not None:
        raise exception_handler.WarningException(f"Contour file for selection {selection.selection_number} already exists.")
    new_file = models.File()
    new_file.insert_path_and_filename(session, contour_file, selection.generate_relative_path(), selection.generate_contour_filename())
    session.add(new_file)
    session.commit()
    print("new file: " + new_file.id)

    # Attribute the new contour file to the selection
    # and reset the traced status
    selection.contour_file = new_file
    selection.update_traced_status()
    print("new file: " + new_file.id)

    selection.recalculate_contour_statistics(session)

    # Create all contour statistics
    #contour_file_obj = contour_code.ContourFile(new_file.get_full_absolute_path(), selection.selection_number)
    #contour_rows = contour_file_obj.calculate_statistics(session, selection)


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
        
        date = database_handler.parse_date(filename)
        # Check if the selection start time matches that of its recording
        recording = session.query(models.Recording).filter(database_handler.db.text("id = :recording_id")).params(recording_id=recording_id).first()
        if not recording.match_start_time(date):
            messages.append("<span style='color: orange;'>Warning: start time mismatch.</span>")
        else:
            messages.append("<span style='color: orange;'>Warning: no start time.</span>")
    
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
        date = database_handler.parse_date(filename)
        if not recording.match_start_time(date):
            messages.append("<span style='color: orange;'>Warning: start time mismatch.</span>")
        else:
            messages.append("<span style='color: orange;'>Warning: no start time.</span>")

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
    fft_size = request.args.get('fft_size', type=int) if request.args.get('fft_size', type=int) else None
    hop_size = request.args.get('hop_size', type=int) if request.args.get('hop_size', type=int) else None
    with database_handler.get_session() as session:
        selection = database_handler.create_system_time_request(session, models.Selection, {"id":selection_id}, one_result=True)
        # Create the file in a temporary path
        with tempfile.TemporaryDirectory(dir=database_handler.get_tempdir()) as temp_dir:
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
    last = request.form.get('last')
    if last == 'true': last = True
    else: last = False
    counter = int(request.form.get('successCounter'))
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
                    counter += 1
                else:
                    raise exception_handler.WarningException("Bad contour number in request")
                session.commit()
            else:
                raise exception_handler.WarningException("Bad file in request")
        except (Exception, SQLAlchemyError) as e:
            exception_handler.handle_exception(session,e)
        finally:
            if last == True:
                if counter > 0:
                    flash(f"Uploaded {counter} contours", 'success')
            return jsonify(successCounter=counter)

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
    
    last = request.form.get('last')
    if last == 'true': last = True
    else: last = False
    counter = int(request.form.get('successCounter'))
    
    success = True
    with database_handler.get_session() as session:
        try:
            if 'file' in request.files and request.files['file'].filename != '':
                file = request.files.get('file')
                id = request.form.get('id')
                current_selection_object = session.query(models.Selection).filter(database_handler.db.text("selection_number = :selection_number and recording_id = :recording_id")).params(selection_number=id, recording_id=recording_id).first()
                if current_selection_object is not None:
                    insert_or_update_selection(session,id, file, recording_id, selection_id=current_selection_object.id)
                else:
                    insert_or_update_selection(session,id, file, recording_id)
                counter += 1
                session.commit()
            else:
                success = False
                raise exception_handler.WarningException("Bad file in request")
        except (Exception,SQLAlchemyError) as e:
            success = False
            exception_handler.handle_exception(session,e)
        finally:
            if last == True:
                if counter > 0:
                    flash(f"Uploaded {counter} selections successfully", "success")
            if success == False:
                return jsonify({'message': '', 'successCounter': counter}), 200
            else:
                return jsonify({'message': '', 'successCounter': counter}), 200

@routes_selection.route('/selection/<selection_id>/download-ctr', methods=['GET'])
def download_ctr_file(selection_id):
    with database_handler.get_session() as session:
        selection = database_handler.create_system_time_request(session, models.Selection, {"id":selection_id}, one_result=True)
        return utils.download_file(selection.ctr_file, selection.generate_ctr_filename)

@routes_selection.route('/selection/<selection_id>/download-contour', methods=['GET'])
def download_contour_file(selection_id):
    with database_handler.get_session() as session:
        selection = database_handler.create_system_time_request(session, models.Selection, {"id":selection_id}, one_result=True)
        return utils.download_file(selection.contour_file, selection.generate_contour_filename)

@routes_selection.route('/selection/<selection_id>/download-selection', methods=['GET'])
def download_selection_file(selection_id):
    with database_handler.get_session() as session:
        selection = database_handler.create_system_time_request(session, models.Selection, {"id":selection_id}, one_result=True)
        return utils.download_file(selection.selection_file, selection.generate_selection_filename)

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


@routes_selection.route('/selection/confirm_no_contour_upload', methods=['POST'])
@database_handler.require_live_session
@login_required
def confirm_no_contour_upload():
    """
    Set traced to False for a selection. This is done when an annotation is Y or M but no contour file
    has been uploaded (i.e. the user has changed their mind on the annotation, and decided not to upload a contour).
    A record is made by setting the traced value of the selection to False.

    :param selection_id: the id of the selection
    :type selection_id: str
    :return: a JSON response with a success message if the selection is updated successfully
    """
    selection_id = request.args.get('selection_id')
    if not selection_id:
        return jsonify({'success': False}),400
    with database_handler.get_session() as session:
        selection = database_handler.create_system_time_request(session, models.Selection, {"id":selection_id})[0]
        selection.traced = False
        session.commit()
        return jsonify({'success': True}),200
    

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
            writer.writerow(selection.generate_contour_stats_array())
    
    output.seek(0)
    return Response(output, mimetype='text/csv', headers={'Content-Disposition': f'attachment; filename="{filename}"'})
    
@routes_selection.route('/recording/<recording_id>/extract_selection_stats', methods=['GET'])
@database_handler.require_live_session
@login_required
def extract_selection_stats(recording_id):
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
        return write_contour_stats(selections, filename=f"ContourStats-{recording.get_start_time_string()}.csv")


@routes_selection.route('/encounter/<encounter_id>/extract_selection_stats', methods=['GET'])
def extract_selection_stats_for_encounter(encounter_id):
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
    with database_handler.get_session() as session:
        selection_ids = request.json.get('selection_ids', [])
        if not selection_ids:
            return jsonify({'error': 'No selection IDs provided'}), 400
        selections = session.query(models.Selection).filter(models.Selection.id.in_(selection_ids)).all()
        success_counter = 0
        for selection in selections:
            try:
                selection.deactivate()
                success_counter += 1
            except Exception as e:
                flash(f'Error deactivating selection {selection.selection_number}: {str(e)}', 'error')
        session.commit()
        if success_counter > 0:
            flash(f'{success_counter} selections deactivated successfully', 'success')
        return jsonify({'success': True})
    
@routes_selection.route('/selection/reactivate', methods=['POST'])
@database_handler.require_live_session
@login_required
@database_handler.exclude_role_4
def reactivate_selections():
    """
    Reactivate selections in the database.

    Expects a JSON payload with a list of selection IDs under the key "selectionIds".
    Returns a JSON response with a message indicating success or failure.
    """
    with database_handler.get_session() as session:
        selection_ids = request.json.get('selection_ids', [])
        if not selection_ids:
            return jsonify({'error': 'No selection IDs provided'}), 400
        selections = session.query(models.Selection).filter(models.Selection.id.in_(selection_ids)).all()
        success_counter = 0
        for selection in selections:
            try:
                selection.reactivate()
                success_counter += 1
            except Exception as e:
                flash(f'Error reactivating selection {selection.selection_number}: {str(e)}', 'error')
        session.commit()
        if success_counter > 0:
            flash(f'{success_counter} selections reactivated successfully', 'success')
        return jsonify({'success': True})