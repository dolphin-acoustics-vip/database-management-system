# Third-party imports
import calendar
from flask import Blueprint, Response, flash,get_flashed_messages, json, jsonify, redirect,render_template,request, send_file,session, url_for, send_from_directory
from sqlalchemy.orm import joinedload,sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from flask_login import login_user,login_required, current_user, login_manager
from flask import session as client_session
from datetime import datetime, timedelta

# Local application imports
import database_handler
from database_handler import get_file_space_path, Session, save_snapshot_date_to_session,require_live_session,exclude_role_1,exclude_role_2,exclude_role_3,exclude_role_4
from models import *
import exception_handler

routes_healthcentre = Blueprint('healthcentre', __name__)

@routes_healthcentre.route('/healthcentre', methods=['GET'])
@login_required
def healthcentre_view():
    with Session() as session:
        species_list = session.query(Species).all()
        return render_template('healthcentre/healthcentre.html', species_list=species_list)



@routes_healthcentre.route('/healthcentre/get-data-warnings', methods=['GET'])
def get_data_warnings():
    statistics_dict = {}
    from models import Selection
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
    
    with Session() as session:

        records = database_handler.get_system_time_request_selection(session, user_id=None, assigned_user_id=assigned_user_id, created_date_filter=created_date_filter_datetime, species_filter_str=species_filter_str, override_snapshot_date=snapshot_date)
        if assigned_user_id:
            user = session.query(User).filter_by(id=uuid.UUID(assigned_user_id)).first()
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