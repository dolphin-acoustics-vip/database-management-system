import re, uuid, zipfile, os
from flask import Blueprint, flash,get_flashed_messages, jsonify, redirect,render_template,request, send_file,session, url_for, send_from_directory
from sqlalchemy.orm import joinedload,sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from db import FILE_SPACE_PATH, Session, GOOGLE_API_KEY
import db
from models import *


routes_encounter = Blueprint('encounter', __name__)


@routes_encounter.route('/encounter/new', methods=['GET'])
def encounter_new():
    session = Session()
    data_sources = session.query(DataSource).all()
    species_list = session.query(Species).all()
    recording_platforms = session.query(RecordingPlatform).all()
    session.close()
    return render_template('encounter/encounter-new.html', species_list=species_list, data_sources=data_sources,recording_platforms=recording_platforms)

@routes_encounter.route('/encounter/insert', methods=['POST'])
def encounter_insert():
    encounter_name = request.form['encounter_name']
    location = request.form['location']
    species_id = request.form['species']
    latitude = request.form['latitude-start']
    longitude = request.form['longitude-start']
    data_source = request.form['data_source']
    recording_platform = request.form['recording_platform']

    origin = request.form['origin']
    notes = request.form['notes']

    session = Session()
    try:
        new_encounter = Encounter()
        new_encounter.set_encounter_name(encounter_name)
        new_encounter.set_location(location)
        new_encounter.set_origin(origin)
        new_encounter.set_notes(notes)
        new_encounter.set_species_id(species_id)
        new_encounter.set_latitude(latitude)
        new_encounter.set_longitude(longitude)
        new_encounter.set_data_source(data_source)
        new_encounter.set_recording_platform(recording_platform)
        session.add(new_encounter)

        session.commit()
        flash(f'Encounter added: {encounter_name}', 'success')
        return redirect(url_for('encounter.encounter_view', encounter_id=new_encounter.id))
    except SQLAlchemyError as e:
        flash(db.parse_alchemy_error(e), 'error')
        session.rollback()
        return redirect(url_for('encounter.encounter'))
    finally:
        session.close()


@routes_encounter.route('/encounter', methods=['GET'])
def encounter():
    session = Session()
    try:
        # Fetch encounter details from the database
        encounter_list = session.query(Encounter).join(Species).all()

        if len(encounter_list) < 1:
            species_data = session.query(Species).all()
            if len(species_data) < 1:
                return render_template('error.html', error_code=404, error_message='No encounter data found. You cannot add encounter data until there are species to add the encounter for.', goback_link='/home', goback_message="Home")

        return render_template('encounter/encounter.html', encounter_list=encounter_list)
    except Exception as e:
        raise e
    finally:
        session.close()

@routes_encounter.route('/encounter/<uuid:encounter_id>/delete', methods=['POST'])
def encounter_delete(encounter_id):
    session = Session()
    encounter = session.query(Encounter).filter_by(id=encounter_id).first()

    try:
        # Delete the encounter from the database
        encounter.delete(session)
        session.commit()
        clean_up_root_directory(ROOT_PATH)
        flash(f'Encounter deleted: {encounter.get_encounter_name()}-{encounter.get_location()}.', 'success')
        return redirect(url_for('encounter.encounter'))
    except SQLAlchemyError as e:
        flash(db.parse_alchemy_error(e), 'error')
        session.rollback()
        return redirect(url_for('encounter.encounter'))
    finally:
        session.close()

@routes_encounter.route('/encounter/<uuid:encounter_id>/view', methods=['GET'])
def encounter_view(encounter_id):
    # Create a new session within the request context
    with Session() as session:
        # Query the Encounter object with the species relationship loaded
        encounter = session.query(Encounter).options(joinedload(Encounter.species)).filter_by(id=encounter_id).first()
        
        # Query the recordings related to the encounter
        recordings = session.query(Recording).filter(Recording.encounter_id == encounter_id).all()

        # No need to manually close the session due to the context manager

        return render_template('encounter/encounter-view.html', encounter=encounter, recordings=recordings, server_side_api_key_variable=GOOGLE_API_KEY)



@routes_encounter.route('/encounter/<uuid:encounter_id>/update', methods=['POST'])
def encounter_update(encounter_id):
    try:
        session = Session()
        encounter = session.query(Encounter).join(Species).filter(Encounter.id == encounter_id).first()
        species_list = session.query(Species).all()
        data_sources = session.query(DataSource).all()
        recording_platforms = session.query(RecordingPlatform).all()


        encounter.set_encounter_name(request.form['encounter_name'])
        encounter.set_location(request.form['location'])
        encounter.set_species_id(request.form['species'])
        encounter.set_origin(request.form['origin'])
        encounter.set_latitude(request.form['latitude-start'])
        encounter.set_longitude(request.form['longitude-start'])
        encounter.set_data_source(request.form['data_source'])
        encounter.set_recording_platform(request.form['recording_platform'])
        encounter.set_notes(request.form['notes'])
        encounter.update_call(session)
        session.commit()
        clean_up_root_directory(FILE_SPACE_PATH)
        flash('Updated encounter: {}.'.format(encounter.encounter_name), 'success')
        return redirect(url_for('encounter.encounter_view', encounter_id=encounter_id))


    except SQLAlchemyError as e:
        flash(db.parse_alchemy_error(e), 'error')
        session.rollback()
        return redirect(url_for('encounter.encounter'))
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


@routes_encounter.route('/encounter/<uuid:encounter_id>/edit', methods=['GET'])
def encounter_edit(encounter_id):
    with Session() as session:
        encounter = session.query(Encounter).join(Species).filter(Encounter.id == encounter_id).first()
        species_list = session.query(Species).all()
        data_sources = session.query(DataSource).all()
        recording_platforms = session.query(RecordingPlatform).all()
        return render_template('encounter/encounter-edit.html', encounter=encounter, species_list=species_list, data_sources=data_sources,recording_platforms=recording_platforms)
