# Third-party imports
from flask import Blueprint, Response, flash,get_flashed_messages, jsonify, redirect,render_template,request, send_file,session, url_for, send_from_directory
from sqlalchemy.orm import joinedload,sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from flask_login import login_user,login_required, current_user, login_manager

# Local application imports
from db import get_file_space_path, Session, GOOGLE_API_KEY, parse_alchemy_error, save_snapshot_date_to_session,require_live_session,exclude_role_1,exclude_role_2,exclude_role_3,exclude_role_4
from models import *
import exception_handler

routes_encounter = Blueprint('encounter', __name__)


@routes_encounter.route('/encounter', methods=['GET'])
@login_required
def encounter():
    with Session() as session:
        try:
            encounter_list = shared_functions.create_system_time_request(session, Encounter, {}, order_by="row_start DESC")
            # If no encounters and no species exist, show an error
            if len(encounter_list) < 1:
                species_data = session.query(Species).all()
                if len(species_data) < 1:
                    return render_template('error.html', error_code=404, error_message='No encounter data found. You cannot add encounter data until there are species to add the encounter for.', goback_link='/home', goback_message="Home")
            return render_template('encounter/encounter.html', encounter_list=encounter_list)
        except SQLAlchemyError as e:
            flash(parse_alchemy_error(e), 'error')
            session.rollback()
            return redirect(url_for('home'))

#@


@routes_encounter.route('/encounter/new', methods=['GET'])
@login_required
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
@require_live_session
def encounter_insert():
    """
    Inserts a new encounter into the database based on the provided form data.
    """
    with Session() as session:

        encounter_name = request.form['encounter_name']
        location = request.form['location']
        species_id = request.form['species']
        latitude = request.form['latitude-start']
        longitude = request.form['longitude-start']
        data_source = request.form['data_source']
        recording_platform = request.form['recording_platform']
        origin = request.form['project']
        notes = request.form['notes']


        data_timezone = request.form['data-timezone']
        location_timezone = request.form['location-timezone']

        try:
            new_encounter = Encounter()
            new_encounter.set_encounter_name(encounter_name)
            new_encounter.set_location(location)
            new_encounter.set_project(origin)
            new_encounter.set_notes(notes)
            new_encounter.set_species_id(species_id)
            new_encounter.set_latitude(latitude)
            new_encounter.set_longitude(longitude)
            new_encounter.set_data_source_id(data_source)
            new_encounter.set_recording_platform_id(recording_platform)
            new_encounter.set_data_timezone(data_timezone)
            new_encounter.set_location_timezone(location_timezone)
            session.add(new_encounter)
            session.commit()
            flash(f'Encounter added: {encounter_name}', 'success')
            return redirect(url_for('encounter.encounter_view', encounter_id=new_encounter.id))
        except SQLAlchemyError as e:
            flash(parse_alchemy_error(e), 'error')
            session.rollback()
            return redirect(url_for('encounter.encounter'))


@routes_encounter.route('/encounter/<uuid:encounter_id>/view', methods=['GET'])
@login_required
def encounter_view(encounter_id):
    """
    Route to show the encounter view page.
    """
    if request.args.get('snapshot_date'):
        save_snapshot_date_to_session(request.args.get('snapshot_date'))

    try:
        with Session() as session:
            encounter = shared_functions.create_system_time_request(session, Encounter, {"id":encounter_id}, one_result=True)
            species = shared_functions.create_system_time_request(session, Species, {"id":encounter.species_id}, one_result=True)
            encounter.species=species

            #encounter = session.query(Encounter).options(joinedload(Encounter.species)).filter_by(id=encounter_id).first()
            #recordings = session.query(Recording).filter(Recording.encounter_id == encounter_id).all()
            
            recordings = shared_functions.create_system_time_request(session, Recording, {"encounter_id":encounter_id})
            if type(recordings) == Response:
                return recordings
            
            encounter_history = shared_functions.create_all_time_request(session, Encounter, {"id":encounter_id}, "row_start")
            
            assignments = shared_functions.create_system_time_request(session, Assignment, {"user_id":current_user.id})
            assignment_recording_ids = [assignment.recording_id for assignment in assignments if assignment.recording_id]
            
            # Filter assigned recordings
            assigned_recordings = [recording for recording in recordings if recording.id in assignment_recording_ids]

            # Filter unassigned recordings
            unassigned_recordings = [recording for recording in recordings if recording.id not in assignment_recording_ids]
            
            recordings.sort(key=lambda x: assignment_recording_ids.index(x.id) if x.id in assignment_recording_ids else len(assignment_recording_ids))

            return render_template('encounter/encounter-view.html', encounter=encounter, recordings=recordings, server_side_api_key_variable=GOOGLE_API_KEY, user=current_user, encounter_history=encounter_history, assignment_recording_ids=assignment_recording_ids,assigned_recordings=assigned_recordings,unassigned_recordings=unassigned_recordings)
    except exception_handler.NotFoundException as e:

        return shared_functions.page_not_found(e, url_for("encounter.encounter_view", encounter_id=encounter_id))
    
@routes_encounter.route('/encounter/<uuid:encounter_id>/edit', methods=['GET'])
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


@routes_encounter.route('/encounter/<uuid:encounter_id>/update', methods=['POST'])
@login_required
@require_live_session
def encounter_update(encounter_id):
    with Session() as session:
        try :
            session = Session()
            encounter = session.query(Encounter).join(Species).filter(Encounter.id == encounter_id).first()
            encounter.set_encounter_name(request.form['encounter_name'])
            encounter.set_location(request.form['location'])
            encounter.set_species_id(request.form['species'])
            encounter.set_project(request.form['project'])
            encounter.set_latitude(request.form['latitude-start'])
            encounter.set_longitude(request.form['longitude-start'])
            encounter.set_data_source_id(request.form['data_source'])
            encounter.set_recording_platform_id(request.form['recording_platform'])
            encounter.set_notes(request.form['notes'])
            encounter.set_data_timezone(request.form['data-timezone'])
            encounter.set_location_timezone(request.form['location-timezone'])
            encounter.update_call(session)
            session.commit()
            flash('Updated encounter: {}.'.format(encounter.encounter_name), 'success')
            return redirect(url_for('encounter.encounter_view', encounter_id=encounter_id))
        except SQLAlchemyError as e:
            flash(parse_alchemy_error(e), 'error')
            session.rollback()
            return redirect(url_for('encounter.encounter'))
        

@routes_encounter.route('/encounter/<uuid:encounter_id>/delete', methods=['POST'])
@login_required
@require_live_session
def encounter_delete(encounter_id):
    with Session() as session:
        encounter = session.query(Encounter).filter_by(id=encounter_id).first()
        recordings = session.query(Recording).filter_by(encounter_id=encounter_id).all()
        if len(recordings) > 0:
            flash('Encounter cannot be deleted. Please delete all recordings first.', 'error')
            return redirect(url_for('encounter.encounter_view', encounter_id=encounter_id))
        else:
            try:
                encounter.delete(session)
                session.commit()
                flash(f'Encounter deleted: {encounter.get_encounter_name()}-{encounter.get_location()}.', 'success')
            except SQLAlchemyError as e:
                flash(parse_alchemy_error(e), 'error')
                session.rollback()
            return redirect(url_for('encounter.encounter'))