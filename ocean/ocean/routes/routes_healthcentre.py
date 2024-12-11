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
import uuid

# Third-party imports
from flask import Blueprint, render_template, request, session as client_session, url_for
from flask_login import login_required
from datetime import datetime, timedelta

# Local application imports
import ocean.database_handler as database_handler
import ocean.models as models

routes_healthcentre = Blueprint('healthcentre', __name__)

@routes_healthcentre.route('/healthcentre', methods=['GET'])
@login_required
def healthcentre_view():
    with database_handler.Session() as session:
        species_list = session.query(models.Species).all()
        return render_template('healthcentre/healthcentre.html', species_list=species_list)



@routes_healthcentre.route('/healthcentre/get-data-warnings', methods=['GET'])
def get_data_warnings():
    statistics_dict = {}
    snapshot_date=client_session.get('snapshot_date')

    snapshot_date_datetime = database_handler.parse_snapshot_date(snapshot_date) if snapshot_date else None
    if snapshot_date_datetime is None:
        snapshot_date_datetime = datetime.now()

    species_filter_str = request.args.get('species_filter')
    assigned_user_id = request.args.get('assigned_user_filter_id')

    created_date_filter = request.args.get('created_date_filter')
    if created_date_filter:
        created_date_filter_datetime = datetime.strptime(created_date_filter, "%Y-%m-%dT%H:%M:%S")
    else:
        created_date_filter_datetime = None

    day_count = request.args.get('day_count')
    if day_count is not None and day_count.isdigit():
        created_date_filter_datetime = snapshot_date_datetime - timedelta(days=int(day_count)-1)
    
    with database_handler.Session() as session:

        records = database_handler.get_system_time_request_selection(session, user_id=None, assigned_user_id=assigned_user_id, created_date_filter=created_date_filter_datetime, species_filter_str=species_filter_str, override_snapshot_date=snapshot_date)
        if assigned_user_id:
            user = session.query(models.User).filter_by(id=uuid.UUID(assigned_user_id)).first()
            user_name= user.name
            user_login_id= user.login_id
        else:
            user_name= None
            user_login_id= None
        warnings = {}
        warning_counter = 0
        total_selections_counter = 0
        def add_warning(selection, warning, warning_counter):
            # if selection['enc_id'] in warnings:
            #     if selection['rec_id'] in warnings[selection['enc_id']]:
            #         if selection['id'] in warnings[selection['enc_id']][selection['rec_id']]:
            #             warnings[selection['enc_id']][selection['rec_id']]['selections'][selection['id']]['warning'].append(warning)
            #         else:
            #             warnings[selection['enc_id']][selection['rec_id']]['selections'].append({'selection': selection, 'warning': [warning]})
            #     else:
            #         warnings[selection['enc_id']][selection['rec_id']] = {'selections': [{'selection': selection, 'warning': [warning]}], 'rec_route': url_for('recording.recording_view', recording_id=selection['rec_id'], encounter_id=selection['enc_id'])}
            # else:
            #     warnings[selection['enc_id']] = {'selections': [{'selection': selection, 'warning': [warning]}], 'rec_route': url_for('recording.recording_view', recording_id=selection['rec_id'], encounter_id=selection['enc_id'])}


            new_warning_sel = {'selection': selection, 'warning': [warning]}

            if selection['enc_id'] not in warnings:
                warnings[selection['enc_id']] = {'enc_name':selection['enc_encounter_name'], 'enc_species': selection['species_name'], 'enc_location': selection['enc_location'], 'recordings': {}}
            if selection['rec_id'] not in warnings[selection['enc_id']]['recordings']:
                warnings[selection['enc_id']]['recordings'][selection['rec_id']] = {'rec_name': selection['rec_start_time'], 'rec_route': url_for('recording.recording_view', recording_id=selection['rec_id']), 'selections': []}

            if len(warnings[selection['enc_id']]['recordings'][selection['rec_id']]['selections']) == 0:
                warnings[selection['enc_id']]['recordings'][selection['rec_id']]['selections'].append(new_warning_sel)
                warning_counter += 1
            else:
                for warning_sel in warnings[selection['enc_id']]['recordings'][selection['rec_id']]['selections']:
                    if warning_sel['selection']['selection_number'] < selection['selection_number']:
                        warnings[selection['enc_id']]['recordings'][selection['rec_id']]['selections'].append(new_warning_sel)
                        warning_counter += 1
                        break
                    elif warning_sel['selection']['id'] == selection['id']:
                        warning_sel['warning'].append(warning)
                        break
            return warning_counter
        
        


        for selection in records:
            total_selections_counter += 1

            #selection_file_valid = not user_id or user_id and selection['sel_file_updated_by_id'] == user_id
            #contour_file_valid = not user_id or user_id and selection['contour_file_updated_by_id'] == user_id

            if selection['selection_file_id'] is None:
                warning_counter=add_warning(selection, "Selection with no file.",warning_counter)
            
            else:
                if selection['traced'] == None and selection['deactivated'] == False:
                    warning_counter=add_warning(selection, "Abandoned selection",warning_counter)
        health_score = 100 - round ((warning_counter / total_selections_counter) * 100) if total_selections_counter > 0 else None
        
        return {'warnings': warnings, 'health_score': health_score, 'warning_counter': warning_counter, 'assigned_user_name': user_name, 'assigned_user_login_id': user_login_id}