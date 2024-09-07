# Third-party imports
from flask import Blueprint, Response, flash,get_flashed_messages, jsonify, redirect,render_template,request, send_file,session, url_for, send_from_directory
from sqlalchemy.orm import joinedload,sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from flask_login import login_user,login_required, current_user, login_manager

# Local application imports
import database_handler
from database_handler import get_file_space_path, Session, save_snapshot_date_to_session,require_live_session,exclude_role_1,exclude_role_2,exclude_role_3,exclude_role_4
from models import *
import exception_handler
from logger import logger
import utils

routes_encounter = Blueprint('encounter', __name__)

@routes_encounter.route('/encounter', methods=['GET'])
@login_required
def encounter():
    with Session() as session:
        try:
            encounter_list = database_handler.create_system_time_request(session, Encounter, {}, order_by="row_start DESC")
            return render_template('encounter/encounter.html', encounter_list=encounter_list)
        except SQLAlchemyError as e:
            exception_handler.handle_sqlalchemy_exception(session, e)
            return redirect(url_for('general.home'))

@routes_encounter.route('/encounter/new', methods=['GET'])
@login_required
@exclude_role_3
@exclude_role_4
@require_live_session
def encounter_new():
    """
    Route to show the new encounter page
    """
    with Session() as session:
        data_sources = session.query(DataSource).all()
        species_list = session.query(Species).all()
        recording_platforms = session.query(RecordingPlatform).all()
        return render_template('encounter/encounter-new.html', species_list=species_list, data_sources=data_sources,recording_platforms=recording_platforms)

@routes_encounter.route('/encounter/insert', methods=['POST'])
@login_required
@exclude_role_3
@exclude_role_4
@require_live_session
def encounter_insert():
    """
    Inserts a new encounter into the database based on the provided form data.
    """
    with Session() as session:
        encounter_form_data = utils.get_form_data({
            'encounter_name': str,
            'location': str,
            'species': str,
            'latitude-start': str,
            'longitude-start': str,
            'data_source': str,
            'recording_platform': str,
            'project': str,
            'notes': str,
            'file-timezone': str,
            'local-timezone': str
        })

        encounter_name = encounter_form_data['encounter_name']
        location = encounter_form_data['location']
        species_id = encounter_form_data['species']
        latitude = encounter_form_data['latitude-start']
        longitude = encounter_form_data['longitude-start']
        data_source_id = encounter_form_data['data_source']
        recording_platform_id = encounter_form_data['recording_platform']
        project = encounter_form_data['project']
        notes = encounter_form_data['notes']
        file_timezone = encounter_form_data['file-timezone']
        local_timezone = encounter_form_data['local-timezone']

        try:
            new_encounter = Encounter()

            new_encounter.set_encounter_name(encounter_name)
            new_encounter.set_location(location)
            new_encounter.set_project(project)
            new_encounter.set_notes(notes)
            new_encounter.set_species_id(session, species_id)
            new_encounter.set_latitude(latitude)
            new_encounter.set_longitude(longitude)
            new_encounter.set_data_source_id(session, data_source_id)
            new_encounter.set_recording_platform_id(session, recording_platform_id)
            new_encounter.set_file_timezone(file_timezone)
            new_encounter.set_local_timezone(local_timezone)

            session.add(new_encounter)
            session.commit()
            flash(f'Encounter added: {encounter_name}', 'success')
            logger.info(f'Encounter added: {new_encounter.id}')
            return redirect(url_for('encounter.encounter_view', encounter_id=new_encounter.id))
        except (Exception,SQLAlchemyError) as e:
            exception_handler.handle_exception(session, e, 'Error inserting encounter')
            return redirect(url_for('encounter.encounter'))


@routes_encounter.route('/encounter/<encounter_id>/view', methods=['GET'])
@login_required
def encounter_view(encounter_id):
    """
    Route to show the encounter view page.
    """
    with Session() as session:
        try:
            encounter = database_handler.create_system_time_request(session, Encounter, {"id":encounter_id}, one_result=True)
            if encounter is None:
                raise exception_handler.NotFoundException("Encounter not found", details="This may be due to a local modification of the web page or an unknown error on the backend. Try reloading the page and if the error persists contact an administrator.")
            species = database_handler.create_system_time_request(session, Species, {"id":encounter.species_id}, one_result=True)
            encounter.species=species
            recordings = database_handler.create_system_time_request(session, Recording, {"encounter_id":encounter_id})
            encounter_history = database_handler.create_all_time_request(session, Encounter, {"id":encounter_id}, "row_start")
            assignments = database_handler.create_system_time_request(session, Assignment, {"user_id":current_user.id})
            assignment_recording_ids = [assignment.recording_id for assignment in assignments if assignment.recording_id]
            assigned_recordings = [recording for recording in recordings if recording.id in assignment_recording_ids]
            unassigned_recordings = [recording for recording in recordings if recording.id not in assignment_recording_ids]
            return render_template('encounter/encounter-view.html', encounter=encounter, encounter_history=encounter_history, assignment_recording_ids=assignment_recording_ids,assigned_recordings=assigned_recordings,unassigned_recordings=unassigned_recordings)
        except (Exception,SQLAlchemyError) as e:
            exception_handler.handle_sqlalchemy_exception(session, e, 'Error viewing encounter')
            return redirect(url_for('encounter.encounter'))

@routes_encounter.route('/encounter/<encounter_id>/edit', methods=['GET'])
@login_required
@require_live_session
def encounter_edit(encounter_id):
    """
    Route to show the encounter edit page.
    """
    with Session() as session:
        encounter = session.query(Encounter).join(Species).filter(Encounter.id == encounter_id).first()
        species_list = session.query(Species).all()
        data_sources = session.query(DataSource).all()
        recording_platforms = session.query(RecordingPlatform).all()
        return render_template('encounter/encounter-edit.html', encounter=encounter, species_list=species_list, data_sources=data_sources,recording_platforms=recording_platforms)


@routes_encounter.route('/encounter/<encounter_id>/update', methods=['POST'])
@login_required
@require_live_session
def encounter_update(encounter_id):
    with Session() as session:
        try :
            encounter = session.query(Encounter).with_for_update().join(Species).filter(Encounter.id == encounter_id).first()
            encounter.set_encounter_name(request.form['encounter_name'])
            encounter.set_location(request.form['location'])
            encounter.set_species_id(session, request.form['species'])
            encounter.set_project(request.form['project'])
            encounter.set_latitude(request.form['latitude-start'])
            encounter.set_longitude(request.form['longitude-start'])
            encounter.set_data_source_id(session, request.form['data_source'])
            encounter.set_recording_platform_id(session, request.form['recording_platform'])
            encounter.set_notes(request.form['notes'])
            encounter.set_file_timezone(request.form['file-timezone'])
            encounter.set_local_timezone(request.form['local-timezone'])
            session.commit()
            encounter.update_call()
            flash('Updated encounter: {}.'.format(encounter.encounter_name), 'success')
            logger.info(f'Encounter updated: {encounter.id}')
            return redirect(url_for('encounter.encounter_view', encounter_id=encounter_id))
        except (SQLAlchemyError,Exception) as e:
            exception_handler.handle_exception(session, e, prefix="Error updating encounter")
            return redirect(url_for('encounter.encounter'))

        

@routes_encounter.route('/encounter/<encounter_id>/delete', methods=['POST'])
@login_required
@require_live_session
def encounter_delete(encounter_id):
    with Session() as session:
        encounter = session.query(Encounter).with_for_update().filter_by(id=encounter_id).first()
        recordings = session.query(Recording).filter_by(encounter_id=encounter_id).all()
        if len(recordings) > 0:
            flash('Encounter cannot be deleted. Please delete all recordings first.', 'error')
            return redirect(url_for('encounter.encounter_view', encounter_id=encounter_id))
        else:
            try:
                encounter.delete_children()
                session.delete(encounter)
                session.commit()
                logger.info(f'Encounter deleted: {encounter.id}')
                flash(f'Encounter deleted: {encounter.get_unique_name("-")}.', 'success')
            except (SQLAlchemyError,Exception) as e:
                exception_handler.handle_exception(session, e, 'Error deleting encounter')
            return redirect(url_for('encounter.encounter'))