# Standard library imports
import re
import shared_functions


# Third-party imports
from flask import Blueprint, flash,get_flashed_messages, jsonify, redirect,render_template,request, send_file,session, url_for, send_from_directory
from sqlalchemy.orm import joinedload,sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from flask_login import login_user,login_required, current_user, login_manager

# Location application imports
from db import FILE_SPACE_PATH, Session, GOOGLE_API_KEY, db, parse_alchemy_error, save_snapshot_date_to_session,require_live_session,exclude_role_1,exclude_role_2,exclude_role_3,exclude_role_4
from models import *
from exception_handler import *

routes_selection = Blueprint('selection', __name__)

def insert_or_update_selection(session, selection_number, file, recording_id, selection_id=None):
    """
    A function to either insert a new Selection object or update an existing one in the database.
    
    Parameters
    - session: the database session
    - selection_number: the number of the selection
    - file: the file to be associated with the selection
    - recording_id: the id of the recording
    - selection_id: the id of the selection (optional, default is None)
    :return: the Selection object that was inserted or updated
    """
    recording = session.query(Recording).filter_by(id=recording_id).first()
    # get Selection object if updating or make a new one if inserting (i.e. selection_id is None)
    if selection_id is not None:
        selection_obj = session.query(Selection).filter_by(id=selection_id).first()
    else:
        selection_obj = Selection()
    selection_obj.recording = recording
    session.add(selection_obj)
    selection_obj.ignore_warnings=False
    selection_obj.set_selection_number(selection_number)
    selection_file = file
    selection_filename = selection_obj.generate_filename()
    selection_relative_path = selection_obj.generate_relative_path()
    new_file = File()
    try:
        new_file.insert_path_and_filename(selection_file, selection_relative_path, selection_filename, FILE_SPACE_PATH)
    except IOError as e:
        if "File already exists" in str(e):
            if session.query(Selection).filter_by(selection_number=selection_number).filter_by(recording_id=recording_id).first() is not None:
                raise IOError (f"Selection {selection_number} for this recording already exists in the database (original file {selection_file.name}).")
            else:
                raise IOError (f"A file with selection {selection_number} for this recording already exists. Cannot overwrite file. Please choose a different selection number or contact administrator to remove the file manually.")
        raise e
    new_file.set_uploaded_date(datetime.now())
    new_file.set_uploaded_by("User 1")
    selection_obj.selection_file = new_file
    selection_obj.selection_file_id = new_file.id
    session.add(new_file)
    return selection_obj


@routes_selection.route('/contour_file_delete/<uuid:selection_id>')
@require_live_session
def contour_file_delete(selection_id):
    with Session() as session:
        selection_obj = session.query(Selection).filter_by(id=selection_id).first()
        selection_obj.delete_contour_file(session)
        #before_commit(session)
        session.commit()
        return redirect(url_for('recording.recording_view', encounter_id=selection_obj.recording.encounter_id, recording_id=selection_obj.recording.id))

@require_live_session
def insert_or_update_contour(session, selection_id, file, recording_id):
    selection_obj = session.query(Selection).filter_by(id=selection_id).first()
    contour_file = file
    contour_filename = selection_obj.generate_contour_filename()
    contour_relative_path = selection_obj.generate_relative_path()
    new_file = File()
    try:
        new_file.insert_path_and_filename(contour_file, contour_relative_path, contour_filename, FILE_SPACE_PATH)
    except IOError as e:
        if "File already exists" in str(e):
            raise IOError (f"Contour {selection_id} for this recording already exists in the database.")
        raise e
    selection_obj.contour_file = new_file

    import calculations.rocca.contour as contour_code
    contour_file_obj = contour_code.ContourFile(new_file.get_full_absolute_path())
    contour_file_obj.calculate_statistics(selection_obj)

    session.add(new_file)
    return selection_obj

@routes_selection.route('/process_contour', methods=["GET"])
@require_live_session
def process_contour():
    recording_id = request.args.get('recording_id')
    filename = request.args.get('filename')
    selection_number = request.args.get('id')
    valid = True
    messages = []
    
    with Session() as session:
        
        # Extract the selection number from the filename using regular expression
        match = re.search(r'sel_(\d+)', filename)
        if match:
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
        
        selection = session.query(Selection).filter(db.text("selection_number = :selection_number and recording_id = :recording_id")).params(selection_number=selection_number, recording_id=recording_id).first()

        if selection:
            if selection.annotation == "N":
                messages.append("<span style='color: orange;'>Selection annotated 'N'. Double check.</span>")
            elif selection.annotation == None:
                messages.append("<span style='color: orange;'>Selection not annotated. Double check selection table.</span>")
        

                
        else:
            messages.append("<span style='color: red;'>Could not cross-reference selection number.</span>")
            valid = False
        
    return jsonify(id=selection_number,messages=messages,valid=valid)


@routes_selection.route('/selection/selection_ignore_warnings/<uuid:selection_id>', methods=['POST'])
@require_live_session
def selection_ignore_warnings(selection_id):
    # Retrieve the selection object based on the selection_id
    selection = Selection.query.get(selection_id)
    
    if selection:
        # Toggle the ignore_warnings value
        selection.ignore_warnings = not selection.ignore_warnings
        db.session.commit()
        
        # Prepare the response data
        response_data = {
            'selection_id': selection_id,
            'ignore_warnings': selection.ignore_warnings
        }
        return jsonify(response_data)
    
    return jsonify({'error': 'Selection not found'}), 404
    

@routes_selection.route('/process_selection', methods=['GET'])
@require_live_session
def process_selection():
    """
    Process the selection of a large number of selection files by the user.
    
    HTTP request arguments:
    - recording_id (str): The ID of the recording to which the selection file will belong.
    - filename (str): The filename of the selection file being processed.
    - selection_number (str): The number of the selection being processed.
    
    Returns:
        A JSON response containing the selection number, a list of messages, and a validity flag.
        - selection_number (str): The selected number.
        - messages (list): A list of messages indicating any warnings or errors encountered during processing.
        - valid (bool): A flag indicating if the selection is valid.
    """
    recording_id = request.args.get('recording_id')
    filename = request.args.get('filename')
    selection_number = request.args.get('id')
    valid = True # flag
    messages=[] # to return at the end
    
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
    with Session() as session:
        if selection_number != None:
            selection_number_exists = session.query(Selection).filter(db.text("selection_number = :selection_number and recording_id = :recording_id")).params(selection_number=selection_number, recording_id=recording_id).first()
            if selection_number_exists:
                if selection_number_exists.selection_file_id is not None:
                    messages.append("<span style='color: red;'>Error: selection number already exists.</span>")
                    valid=False
                
            
        
        # Check if the selection start time matches that of its recording
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
                messages.append("<span style='color: orange;'>Warning: start time mismatch.</span>")
        else:
            messages.append("<span style='color: orange;'>Warning: no start time.</span>")
    
        ## TODO: Add check if selection already uploaded
    


    return jsonify(id=selection_number,messages=messages,valid=valid)


@routes_selection.route('/encounter/<uuid:encounter_id>/recording/<uuid:recording_id>/contour/insert-bulk', methods=['GET', 'POST'])
@require_live_session
def contour_insert_bulk(encounter_id, recording_id):
    with Session() as session:
        try:
            if 'files' not in request.files:
                return jsonify({'error': 'No files found'}), 400

            # Access the uploaded files
            files = request.files.getlist('files')
            ids = [request.form.get(f'ids[{i}]') for i in range(len(files ))]

            # Process the files and add them to the Selection object
            for i, file in enumerate(files):
                try:
                    selection = session.query(Selection).filter(db.text("selection_number = :selection_number and recording_id = :recording_id")).params(selection_number=ids[i], recording_id=recording_id).first()

                    insert_or_update_contour(session,selection.id, file, recording_id)
                    #before_commit(session)
                    session.commit()
                    flash(f'Added contour {ids[i]}', 'success')
                except SQLAlchemyError as e:
                    session.rollback()
                    raise e
                    flash(f'Error inserting contour {ids[i]}: {e}', 'error')
        except Exception as e:
            session.rollback()
            raise e
            flash(f'Error inserting contour: {e}', 'error')
    return redirect(url_for('recording.recording_view', encounter_id=encounter_id, recording_id=recording_id))

@routes_selection.route('/encounter/<uuid:encounter_id>/recording/<uuid:recording_id>/selection/insert-bulk', methods=['GET', 'POST'])
@require_live_session
def selection_insert_bulk(encounter_id,recording_id):
    """
    Inserts multiple selection files into the database for a given encounter ID and recording ID.
    
    Note that the metadata for these selection files should first be checked using the /process_selection GET route.
    
    Returns:
        A JSON response indicating success or failure.
    """
    
    
    with Session() as session:
        try:
            if 'files' not in request.files:
                return jsonify({'error': 'No files found'}), 400

            # Access the uploaded files
            files = request.files.getlist('files')
            ids = [request.form.get(f'ids[{i}]') for i in range(len(files ))]

            counter = 0
            # Process the files and add them to the Selection object
            for i, file in enumerate(files):
                try:
                    current_selection_object = session.query(Selection).filter(db.text("selection_number = :selection_number and recording_id = :recording_id")).params(selection_number=ids[i], recording_id=recording_id).first()
                    if current_selection_object is not None:
                        insert_or_update_selection(session,ids[i], file, recording_id, selection_id=current_selection_object.id)
                    else:
                        insert_or_update_selection(session,ids[i], file, recording_id)
                    #before_commit(session)
                    session.commit()
                    counter += 1
                except SQLAlchemyError as e:
                    handle_sqlalchemy_exception(session, e)
                except IOError as e:
                    handle_sqlalchemy_exception(session, e)
            #before_commit(session)
            session.commit()
            flash(f'Added {counter} selections', 'success')
            return jsonify({'message': 'Files uploaded successfully'}), 200
        except SQLAlchemyError as e:
            flash(parse_alchemy_error(e), 'error')
            return jsonify({'error': str(e)}), 500
        except IOError as e:
            flash(str(e), 'error')
            return jsonify({'error': str(e)}), 500
        
        


@routes_selection.route('/selection/<uuid:selection_id>/view', methods=['GET'])
def selection_view(selection_id):
    """
    Renders the recording view page for a specific encounter and recording.
    """
    if request.args.get('snapshot_date'):
        save_snapshot_date_to_session(request.args.get('snapshot_date'))
    
    with Session() as session:
        
        selection = shared_functions.create_system_time_request(session, Selection, {"id":selection_id})[0]
        selection_history = shared_functions.create_all_time_request(session, Selection, filters={"id":selection_id}, order_by="row_start")

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
