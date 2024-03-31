import re, uuid, zipfile, os
from flask import Blueprint, flash,get_flashed_messages, jsonify, redirect,render_template,request, send_file,session, url_for, send_from_directory
from sqlalchemy.orm import joinedload,sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from db import UPLOAD_FOLDER, Session, GOOGLE_API_KEY
import db
from models import *


routes_selection = Blueprint('selection', __name__)


def insert_or_update_selection(session, selection_number, file, recording_id, selection_id=None):
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


@routes_selection.route('/process_selection', methods=['GET'])
def process_selection_number():
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


@routes_selection.route('/encounter<uuid:encounter_id>/recording/<uuid:recording_id>/selection/insert-bulk', methods=['GET', 'POST'])
def selection_insert_bulk(encounter_id,recording_id):
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


                    insert_or_update_selection(session,selection_numbers[i], file, recording_id)
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
    