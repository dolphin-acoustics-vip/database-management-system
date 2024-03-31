import re, uuid, zipfile, os
from flask import Blueprint, flash,get_flashed_messages, jsonify, redirect,render_template,request, send_file,session, url_for, send_from_directory
from sqlalchemy.orm import joinedload,sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from db import FILE_SPACE_PATH, Session, GOOGLE_API_KEY
import db
from models import *


routes_recording = Blueprint('recording', __name__)



def insert_or_update_recording(session, request, encounter_id, recording_id=None):
    encounter = session.query(Encounter).filter_by(id=encounter_id).first()
    root_path = FILE_SPACE_PATH

    time_start = request.form['time_start']
    seconds = request.form['seconds']

    if recording_id is not None:
        new_recording = session.query(Recording).filter_by(id=recording_id).first()
    else:
        new_recording = Recording()

    new_recording.set_start_time(time_start, seconds)
    new_recording.set_duration(0)
    new_recording.set_encounter_id(encounter_id)
    session.add(new_recording)
    session.commit()

    # Handle recording file
    if 'recording_file' in request.files and request.files['recording_file'].filename != '':
        recording_file = request.files['recording_file']

        new_recording_filename = new_recording.generate_recording_filename()
        new_relative_path = new_recording.generate_relative_path()
        new_file = File()
        new_file.insert_path_and_filename(recording_file, new_relative_path, new_recording_filename, root_path)
        new_file.set_uploaded_date = datetime.now()
        new_file.set_uploaded_by("User 1")
        session.add(new_file)

        new_recording.recording_file = new_file

    # Handle selection file
    if 'selection_file' in request.files and request.files['selection_file'].filename != '':
        selection_file = request.files['selection_file']

        new_selection_filename = new_recording.generate_selection_filename()
        new_relative_path = new_recording.generate_relative_path()
        new_file = File()
        new_file.insert_path_and_filename(selection_file, new_relative_path, new_selection_filename, root_path)
        new_file.set_uploaded_date = datetime.now()
        new_file.set_uploaded_by("User 1")
        session.add(new_file)

        new_recording.selection_file = new_file

    session.commit()

    return new_recording


@routes_recording.route('/encounter/<uuid:encounter_id>/recording/insert', methods=['POST'])
def recording_insert(encounter_id):
    session = Session()
    try:
        recording_obj = insert_or_update_recording(session, request, encounter_id)
        session.add(recording_obj)
        session.commit()
        flash(f'Added recording: {recording_obj.id}', 'success')
        return redirect(url_for('encounter.encounter_view', encounter_id=encounter_id))
    except SQLAlchemyError as e:
        flash(db.parse_alchemy_error(e), 'error')
        session.rollback()
        return redirect(url_for('encounter.encounter_view', encounter_id=encounter_id))
    finally:
        session.close()



@routes_recording.route('/encounter/<uuid:encounter_id>/recording/<uuid:recording_id>/view', methods=['GET'])
def recording_view(encounter_id,recording_id):
    with Session() as session:
        recording = session.query(Recording).filter_by(id=recording_id).first()
        selections = session.query(Selection).filter_by(recording_id=recording_id).order_by(Selection.selection_number).all()
        return render_template('recording/recording-view.html', recording=recording, selections=selections)



@routes_recording.route('/encounter/<uuid:encounter_id>/recording/<uuid:recording_id>/update', methods=['POST'])
def recording_update(encounter_id, recording_id):
    with Session() as session:
        try:
            recording_obj = insert_or_update_recording(session, request, encounter_id, recording_id)
            recording_obj.update_call(session)

            session.commit()
            clean_up_root_directory(os.path.join(ROOT_PATH,recording_obj.generate_relative_path()))
            flash(f'Edited recording: {recording_obj.id}', 'success')                
            return redirect(url_for('encounter.encounter_view', encounter_id=encounter_id))
        except SQLAlchemyError as e:
            flash(db.parse_alchemy_error(e), 'error')
            session.rollback()
            return redirect(url_for('encounter.encounter_view', encounter_id=encounter_id))
        finally:
            session.close()

@routes_recording.route('/encounter/<uuid:encounter_id>/recording/<uuid:recording_id>/delete', methods=['POST'])
def recording_delete(encounter_id,recording_id):
    with Session() as session:
        try:
            recording = session.query(Recording).filter_by(id=recording_id).first()
            recording.delete(session)
            session.commit()
            flash(f'Deleted recording: {recording.id}', 'success')
            return redirect(url_for('encounter.encounter_view', encounter_id=encounter_id))
        except SQLAlchemyError as e:
            flash(db.parse_alchemy_error(e), 'error')
            session.rollback()
            return redirect(url_for('encounter.encounter_view', encounter_id=encounter_id))
        finally:
            session.close()


@routes_recording.route('/encounter/<uuid:encounter_id>/recording/<uuid:recording_id>/recording-file/<uuid:file_id>/delete',methods=['POST','DELETE'])
def recording_file_delete(encounter_id,recording_id,file_id):
    with Session() as session:
        try:
            recording = session.query(Recording).filter_by(recording_file_id=file_id).first()
            recording.recording_file=None
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
            flash(db.parse_alchemy_error(e), 'error')
            session.rollback()
            return redirect(url_for('encounter.encounter_view', encounter_id=encounter_id))
        finally:
            session.close()



@routes_recording.route('/recording/<uuid:recording_id>/recording_delete_selections', methods=['DELETE'])
def recording_delete_selections(recording_id):
    if request.method == 'DELETE':
        data = request.get_json()
        selection_ids = data.get('selectionIds', [])
        
        session = Session()
        try:
            for selection_id in selection_ids:
                selection_id = uuid.UUID(selection_id)  # Convert the string to a UUID object

                selection = session.query(Selection).filter_by(id=selection_id).first()
                selection_number = selection.selection_number
                selection.delete(session)
                flash(f'Deleted selection: {selection_number}', 'success')

            session.commit()
            return jsonify({'message': 'Bulk delete completed'}), 200
        except SQLAlchemyError as e:
            session.rollback()
            flash(db.parse_alchemy_error(e), 'error')
            return jsonify({'error': db.parse_alchemy_error(e)}), 500
        finally:
            session.close()
    else:
        return jsonify({'error': 'Method not allowed'}), 405


         
@routes_recording.route('/encounter/<uuid:encounter_id>/recording/<uuid:recording_id>/selection-file/<uuid:file_id>/delete')
def selection_file_delete(encounter_id,recording_id,file_id):
    with Session() as session:
        try:
            recording = session.query(Recording).filter_by(selection_file_id=file_id).first()
            recording.selection_file=None
            
            file = session.query(File).filter_by(id=file_id).first()
            try:
                file_path = file.get_full_relative_path()
                file.move_to_trash()
                session.delete(file)
                session.commit()
                flash(f'Deleted file: {file_path}', 'success')

            except FileNotFoundError:
                session.commit()
                flash(f'Deleted file record but could not find file: {file_path}', 'success')
            
            return redirect(url_for('view_encounter', encounter_id=encounter_id))
        except SQLAlchemyError as e:
            flash(db.parse_alchemy_error(e), 'error')
            session.rollback()
            return redirect(url_for('view_encounter', encounter_id=encounter_id))
        finally:
            session.close()

