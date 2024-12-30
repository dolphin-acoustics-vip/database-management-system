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
from flask import Blueprint, flash, redirect, render_template, request, url_for
from sqlalchemy.exc import SQLAlchemyError
from flask_login import login_required, current_user

# Local application imports
from .. import database_handler
from .. import models
from .. import exception_handler
from .. import utils
from .. import response_handler
from ..logger import logger

routes_encounter = Blueprint('encounter', __name__)

@routes_encounter.route('/encounter', methods=['GET'])
@login_required
def encounter():
    with database_handler.get_session() as session:
        try:
            encounter_list = database_handler.create_system_time_request(session, models.Encounter, {}, order_by="row_start DESC")
            return render_template('encounter/encounter.html', encounter_list=encounter_list)
        except SQLAlchemyError as e:
            exception_handler.handle_exception(exception=e, session=session)
            return redirect(url_for('general.home'))

@routes_encounter.route('/encounter/new', methods=['GET'])
@login_required
@database_handler.exclude_role_3
@database_handler.exclude_role_4
@database_handler.require_live_session
def encounter_new():
    """
    Route to show the new encounter page
    """
    with database_handler.get_session() as session:
        data_sources = session.query(models.DataSource).all()
        species_list = session.query(models.Species).all()
        recording_platforms = session.query(models.RecordingPlatform).all()
        return render_template('encounter/encounter-new.html', species_list=species_list, data_sources=data_sources,recording_platforms=recording_platforms)

@routes_encounter.route('/encounter/insert', methods=['POST'])
@login_required
@database_handler.exclude_role_3
@database_handler.exclude_role_4
@database_handler.require_live_session
def encounter_insert():
    """ Route to insert a new encounter. The response is created using response_handler.JSONResponse. If the insertion
    is successful, a message is added to flask.flash() and a redirect link is passed to the JSONResponse. If the insertion
    fails, an error message is added to the JSONResponse and no redirect link is passed to the JSONResponse (this is because
    the user should not be redirected, but rather instructed to fix the issue that caused the error).

    Requires the following form fields:
    encounter_name: str (not empty or None)
    location: str (not empty or None)
    species: str (not empty or None and a valid UUID pointing to a Species)
    latitude-start: str
    longitude-start: str
    data_source: str (none or a valid UUID pointing to a DataSource)
    recording_platform: str (None or a valid UUID pointing to a RecordingPlatform)
    project: str (not empty or None)
    notes: str

    Returns:
        flask.Response: The JSON response
    """
    response = response_handler.JSONResponse()
    with database_handler.get_session() as session:
        # Verify required fields of the form are present
        encounter_form_data = utils.get_form_data(request, {
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

        try:
            new_encounter = models.Encounter()
            new_encounter.set_encounter_name(encounter_form_data['encounter_name'])
            new_encounter.set_location(encounter_form_data['location'])
            new_encounter.set_project(encounter_form_data['project'])
            new_encounter.set_notes(encounter_form_data['notes'])
            new_encounter.set_species_id(encounter_form_data['species'])
            new_encounter.set_latitude(encounter_form_data['latitude-start'])
            new_encounter.set_longitude(encounter_form_data['longitude-start'])
            new_encounter.set_data_source_id(encounter_form_data['data_source'])
            new_encounter.set_recording_platform_id(encounter_form_data['recording_platform'])
            new_encounter.set_file_timezone(encounter_form_data['file-timezone'])
            new_encounter.set_local_timezone(encounter_form_data['local-timezone'])
            session.add(new_encounter)
            session.commit()
            flash(f'Inserted {new_encounter.get_unique_name()}.', 'success')
            logger.info(f'Inserted {new_encounter.get_unique_name()}.')
            response.set_redirect(url_for('encounter.encounter_view', encounter_id=new_encounter.id))
            return response.to_json()
        except (Exception,SQLAlchemyError) as e:
            response.add_error(exception_handler.handle_exception(exception=e, prefix='Error inserting encounter', session=session, show_flash=False))
            return response.to_json()


@routes_encounter.route('/encounter/<encounter_id>/view', methods=['GET'])
@login_required
def encounter_view(encounter_id):
    """
    Route to show the encounter view page.
    """
    with database_handler.get_session() as session:
        try:
            encounter = database_handler.create_system_time_request(session, models.Encounter, {"id":encounter_id}, one_result=True)
            if not encounter:
                raise exception_handler.CriticalException(f"Encounter not found.")
            species = database_handler.create_system_time_request(session, models.Species, {"id":encounter.species_id}, one_result=True)
            encounter.species=species
            recordings = database_handler.create_system_time_request(session, models.Recording, {"encounter_id":encounter_id})
            encounter_history = database_handler.create_all_time_request(session, models.Encounter, {"id":encounter_id}, "row_start")
            assignments = database_handler.create_system_time_request(session, models.Assignment, {"user_id":current_user.id})
            assignment_recording_ids = [assignment.recording_id for assignment in assignments if assignment.recording_id]
            assigned_recordings = [recording for recording in recordings if recording.id in assignment_recording_ids]
            unassigned_recordings = [recording for recording in recordings if recording.id not in assignment_recording_ids]
            return render_template('encounter/encounter-view.html', encounter=encounter, encounter_history=encounter_history, assignment_recording_ids=assignment_recording_ids,assigned_recordings=assigned_recordings,unassigned_recordings=unassigned_recordings)
        except (Exception,SQLAlchemyError) as e:
            exception_handler.handle_exception(exception=e, prefix="Error viewing encounter", session=session)
            return redirect(url_for('encounter.encounter'))

@routes_encounter.route('/encounter/<encounter_id>/edit', methods=['GET'])
@login_required
@database_handler.require_live_session
def encounter_edit(encounter_id):
    with database_handler.get_session() as session:
        encounter = session.query(models.Encounter).join(models.Species).filter(models.Encounter.id == encounter_id).first()
        species_list = session.query(models.Species).all()
        data_sources = session.query(models.DataSource).all()
        recording_platforms = session.query(models.RecordingPlatform).all()
        return render_template('encounter/encounter-edit.html', encounter=encounter, species_list=species_list, data_sources=data_sources,recording_platforms=recording_platforms)


@routes_encounter.route('/encounter/<encounter_id>/update', methods=['POST'])
@login_required
@database_handler.require_live_session
def encounter_update(encounter_id):
    """ Route to update an encounter. The response is created using response_handler.JSONResponse. If the update
    is successful, a message is added to flask.flash() and a redirect link is passed to the JSONResponse. If the update
    fails, an error message is added to the JSONResponse and no redirect link is passed to the JSONResponse (this is because
    the user should not be redirected, but rather instructed to fix the issue that caused the error).

    Requires the following form fields:
    encounter_name: str (not empty or None)
    location: str (not empty or None)
    species: str (not empty or None and a valid UUID pointing to a Species)
    latitude-start: str
    longitude-start: str
    data_source: str (none or a valid UUID pointing to a DataSource)
    recording_platform: str (None or a valid UUID pointing to a RecordingPlatform)
    project: str (not empty or None)
    notes: str

    Args:
        encounter_id (str): The ID of the encounter to update

    Returns:
        flask.Response: The JSON response
    """
    response = response_handler.JSONResponse()
    with database_handler.get_session() as session:
        try :
            encounter = session.query(models.Encounter).with_for_update().join(models.Species).filter(models.Encounter.id == encounter_id).first()
            encounter.set_encounter_name(request.form['encounter_name'])
            encounter.set_location(request.form['location'])
            encounter.set_species_id(request.form['species'])
            encounter.set_project(request.form['project'])
            encounter.set_latitude(request.form['latitude-start'])
            encounter.set_longitude(request.form['longitude-start'])
            encounter.set_data_source_id(request.form['data_source'])
            encounter.set_recording_platform_id(request.form['recording_platform'])
            encounter.set_notes(request.form['notes'])
            encounter.set_file_timezone(request.form['file-timezone'])
            encounter.set_local_timezone(request.form['local-timezone'])
            session.commit()
            encounter.update_call()
            flash('Updated {}.'.format(encounter.get_unique_name()), 'success')
            logger.info(f'Updated {encounter.id}.')
            response.set_redirect(url_for('encounter.encounter_view', encounter_id=encounter_id))
            return response.to_json()
        except (SQLAlchemyError,Exception) as e:
            response.add_error(exception_handler.handle_exception(exception=e, prefix="Error updating encounter", session=session, show_flash=False))
            return response.to_json()

        

@routes_encounter.route('/encounter/<encounter_id>/delete', methods=['POST'])
@login_required
@database_handler.require_live_session
def encounter_delete(encounter_id):
    response = response_handler.JSONResponse()
    with database_handler.get_session() as session:
        encounter = session.query(models.Encounter).with_for_update().filter_by(id=encounter_id).first()
        recordings = session.query(models.Recording).filter_by(encounter_id=encounter_id).all()
        if len(recordings) > 0:
            response.add_error('Encounter cannot be deleted. Please delete all recordings first.')
        else:
            try:
                unique_name = encounter.get_unique_name()
                encounter.delete_children()
                session.delete(encounter)
                session.commit()
                logger.info(f'Deleted {unique_name}.')
                flash(f'Deleted {unique_name}.', 'success')
                response.set_redirect(url_for('encounter.encounter'))
            except (SQLAlchemyError,Exception) as e:
                response.add_error(exception_handler.handle_exception(exception=e, prefix='Error deleting encounter', session=session))
    return response.to_json()