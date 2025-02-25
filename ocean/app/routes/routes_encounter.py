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
from .. import transaction_handler
from ..logger import logger

routes_encounter = Blueprint('encounter', __name__)

@routes_encounter.route('/encounter', methods=['GET'])
@login_required
def encounter():
    """GET route to show the page with a list of all encounters."""
    
    with database_handler.get_session() as session:
        from ..models import File
        File.get_abandoned_files(session)
        try:
            encounter_list = database_handler.create_system_time_request(session, models.Encounter, {}, order_by="row_start DESC")
            return render_template('encounter/encounter.html', encounter_list=encounter_list)
        except Exception as e:
            exception_handler.handle_exception(exception=e, session=session)
            return redirect(url_for('general.home'))

@routes_encounter.route('/encounter/new', methods=['GET'])
@login_required
@database_handler.exclude_role_3
@database_handler.exclude_role_4
@database_handler.require_live_session
def encounter_new():
    """GET route to show the page to add a new encounter."""

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
    with response_handler.json_response_context() as response:
        with transaction_handler.atomic() as session:
            encounter = models.Encounter()
            encounter.insert(request.form)
            session.add(encounter)
            flash_message = f'Inserted encounter {encounter.unique_name}.'
        flash(flash_message, 'success')
        response.set_redirect(url_for('encounter.encounter'))
    return response.to_json()

@routes_encounter.route('/encounter/<encounter_id>/view', methods=['GET'])
@login_required
def encounter_view(encounter_id):
    with database_handler.get_session() as session:
        try:
            encounter = database_handler.create_system_time_request(session, models.Encounter, {"id":encounter_id}, one_result=True)
            if not encounter: raise exception_handler.DoesNotExistError("encounter")            
            recordings = database_handler.create_system_time_request(session, models.Recording, {"encounter_id":encounter_id})
            encounter_history = database_handler.create_all_time_request(session, models.Encounter, {"id":encounter_id}, "row_start")
            assignments = database_handler.create_system_time_request(session, models.Assignment, {"user_id":current_user.id})
            assignment_recording_ids = [assignment.recording_id for assignment in assignments if assignment.recording_id]
            assigned_recordings = [recording for recording in recordings if recording.id in assignment_recording_ids]
            unassigned_recordings = [recording for recording in recordings if recording.id not in assignment_recording_ids]
            return render_template('encounter/encounter-view.html', encounter=encounter, encounter_history=encounter_history, assignment_recording_ids=assignment_recording_ids,assigned_recordings=assigned_recordings,unassigned_recordings=unassigned_recordings)
        except Exception as e:
            exception_handler.handle_exception(exception=e, prefix="Error viewing encounter", session=session)
            return redirect(url_for('encounter.encounter'))

@routes_encounter.route('/encounter/<encounter_id>/edit', methods=['GET'])
@login_required
@database_handler.require_live_session
def encounter_edit(encounter_id):
    """GET route to show the page to edit an encounter."""\
    
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
    with response_handler.json_response_context() as response:
        with transaction_handler.atomic() as session:
            encounter = session.query(models.Encounter).with_for_update().join(models.Species).filter(models.Encounter.id == encounter_id).first()
            encounter.update(request.form)
            flash_message = f"Updated encounter {encounter.unique_name}."
            encounter.apply_updates()
        flash(flash_message, 'success')
        response.set_redirect(url_for('encounter.encounter_view', encounter_id=encounter_id))
    return response.to_json()

        

@routes_encounter.route('/encounter/<encounter_id>/delete', methods=['POST'])
@login_required
@database_handler.require_live_session
def encounter_delete(encounter_id):
    """POST route to delete an encounter. Returns JSON following `response_handler.JSONResponse` protocol."""

    response = response_handler.JSONResponse()
    with database_handler.get_session() as session:
        encounter = session.query(models.Encounter).with_for_update().filter_by(id=encounter_id).first()
        try:
            unique_name = encounter.unique_name
            encounter.delete(session)
            session.commit()
            flash(f'Deleted {unique_name}.', 'success')
            response.set_redirect(url_for('encounter.encounter'))
        except Exception as e:
            response.add_error(exception_handler.handle_exception(exception=e, prefix='Error deleting encounter', session=session))
    return response.to_json()

@routes_encounter.route('/encounter/<encounter_id>/download-ctr-files', methods=['GET'])
@login_required
def download_ctr_files(encounter_id):
    """Download CTR files for all recordings in an encounter."""
    with database_handler.get_session() as session:
        encounter = session.query(models.Encounter).filter_by(id=encounter_id).first()
        zip_filename = f"{encounter.species.scientific_name}-{encounter.encounter_name}-{encounter.location}_ctr_files.zip"
        return utils.stream_zip_file(encounter.generate_ctr_files, zip_filename)