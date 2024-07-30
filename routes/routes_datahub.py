# Third-party imports
import calendar
from flask import Blueprint, Response, flash,get_flashed_messages, json, jsonify, redirect,render_template,request, send_file,session, url_for, send_from_directory
from sqlalchemy.orm import joinedload,sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from flask_login import login_user,login_required, current_user, login_manager
from flask import session as client_session
from datetime import datetime, timedelta

# Local application imports
from db import FILE_SPACE_PATH, Session, GOOGLE_API_KEY, parse_alchemy_error, save_snapshot_date_to_session,require_live_session,exclude_role_1,exclude_role_2,exclude_role_3,exclude_role_4
from models import *
import exception_handler

routes_datahub = Blueprint('datahub', __name__)


@routes_datahub.route('/datahub', methods=['GET'])
@login_required
def datahub_view():
    with Session() as session:
        species_list = session.query(Species).all()
        return render_template('datahub/datahub.html', species_list=species_list)


@routes_datahub.route('/datahub/get-selection-statistics', methods=['GET'])
def get_selection_statistics():
    data = request.args.get('data')  # Get the data from the query parameters
    with Session() as session:
        return jsonify(selections=session.query(Selection).count())


daily_axis_label_format = "%d %b %Y"
monthly_axis_label_format = "%b %Y"
def create_date_axis_labels(start_date, end_date):
    """
    Generate date axis labels based on the given start and end dates.

    Args:
        start_date (datetime): The start date of the date range.
        end_date (datetime): The end date of the date range.

    Returns:
        tuple: A tuple containing two elements:
            1. labels (list): A list of formatted date strings representing the axis labels.
            2. category_months (bool): A boolean indicating whether the axis labels are categorized by months.

    """
    category_months = abs((start_date - end_date).days) > 90
    labels = []
    if not category_months:
        # Generate sorted array of dates in between the start date and end date
        labels = [date.strftime(daily_axis_label_format) for date in [end_date - timedelta(days=x) for x in range(0, (end_date - start_date).days + 1)]][::-1]
    else:
        # Generate sorted array of months in between the start date and end date
        labels = [date.strftime(monthly_axis_label_format) for date in sorted({date.replace(day=1) for date in set(start_date + timedelta(days=x) for x in range(0, (end_date - start_date).days + 1)) if (date.replace(day=1) <= end_date)}, key=lambda x: (x.year, x.month))]
    return labels, category_months


# @routes_datahub.route('/datahub/get-statistics-for-user', methods=['GET'])
# def get_statistics_for_user():
#     user_id = request.args.get('user_id')
#     start_date_time = request.args.get('start_date_time')
#     start_date_time = datetime.strptime(start_date_time, "%Y-%m-%dT%H:%M:%S")
#     columns = "sel.id, sel.selection_number, sel.row_start, sel.row_end, sel.selection_file_id, sel.contour_file_id, sel_file.filename sel_file_filename, sel_file.upload_datetime sel_file_upload_datetime, sel_file.updated_by_id sel_file_updated_by_id, contour_file.filename contour_file_filename, contour_file.upload_datetime contour_file_upload_datetime, contour_file.updated_by_id contour_file_updated_by_id, sel_file_user.id sel_file_user_id, sel_file_user.login_id sel_file_user_login_id, sel_file_user.name sel_file_user_name, contour_file_user.id contour_file_user_id, contour_file_user.name contour_file_user_name, contour_file_user.login_id contour_file_user_login_id"
#     joins = "LEFT JOIN file AS sel_file ON sel_file.id = sel.selection_file_id LEFT JOIN file AS contour_file ON contour_file.id = sel.contour_file_id LEFT JOIN user AS sel_file_user ON sel_file.updated_by_id = sel_file_user.id LEFT JOIN user AS contour_file_user ON contour_file.updated_by_id = contour_file_user.id"
#     with Session() as session:
#         snapshot_date=client_session.get('snapshot_date')
#         if snapshot_date: query_str="SELECT {} FROM {} FOR SYSTEM_TIME AS OF '{}'".format(columns, Selection.__tablename__, snapshot_date)
#         else: query_str="SELECT {} FROM {} AS sel".format(columns, Selection.__tablename__)
#         query_str += " {}".format(joins)
#         query = db.text(query_str)
#         result = session.execute(query)

@routes_datahub.route('/datahub/get-statistics', methods=['GET'])
def get_statistics():
    statistics_dict = {}
    from models import Selection
    snapshot_date=client_session.get('snapshot_date')

    snapshot_date_datetime = datetime.strptime(snapshot_date, "%Y-%m-%d %H:%M:%S.%f") if snapshot_date else None       
    if snapshot_date_datetime is None:
        snapshot_date_datetime = datetime.now()

    species_filter_str = request.args.get('species_filter')


    start_date_time = request.args.get('start_date_time')
    start_date_time = datetime.strptime(start_date_time, "%Y-%m-%dT%H:%M:%S")
    day_count = request.args.get('day_count')
    if day_count is not None and day_count.isdigit():
        start_date_time = snapshot_date_datetime - timedelta(days=int(day_count)-1)
    end_date_time = snapshot_date_datetime
    user_id = request.args.get('user_id')


    
    with Session() as session:

        records = shared_functions.get_system_time_request_with_joins(session, user_id=user_id, species_filter_str=species_filter_str, override_snapshot_date=snapshot_date)
        if user_id:
            user = session.query(User).filter_by(id=uuid.UUID(user_id)).first()
            statistics_dict['user_name'] = user.name
            statistics_dict['user_login_id'] = user.login_id
        
        num_selection_files = 0
        num_selection_file_uploads = 0
        num_contour_files = 0
        num_contour_file_uploads = 0
       

        start_date = start_date_time.date()
        end_date = end_date_time.date()
        number_days = (int((end_date - start_date).days) + 1)
        axis_labels, category_months = create_date_axis_labels(start_date, end_date)
        
        selection_file_insert_list = [0] * len(axis_labels)
        contour_file_insert_list = [0] * len(axis_labels)

        selection_user_contributions = {}
        contour_user_contributions = {}

        annotation_acceptance_rate = None
        traced_true_match_count = 0
        traced_true_unmatch_count = 0
        traced_false_match_count = 0
        traced_false_unmatch_count = 0

        contoured_same_selection_count = 0
        abandoned_plus_week_selection_count = 0
        abandoned_less_week_selection_count = 0

        species_complete_counter = {}
        complete_counter = 0

        for selection in records:
            selection_file_valid = not user_id or user_id and selection['sel_file_updated_by_id'] == user_id
            contour_file_valid = not user_id or user_id and selection['contour_file_updated_by_id'] == user_id


            if selection['sel_created_datetime'] > start_date_time:
                if selection['selection_file_id'] is None or selection['traced'] is None:
                    print(selection['sel_updated_by_id'], user_id)
                    if not user_id or user_id and selection['sel_updated_by_id'] == user_id:
                        if selection['sel_created_datetime'] < end_date_time - timedelta(days=7):
                            abandoned_plus_week_selection_count += 1
                        else:
                            abandoned_less_week_selection_count += 1                        


            if selection['selection_file_id'] is not None:
                if selection_file_valid: 

                    


                    num_selection_files += 1


                    if selection['sel_file_upload_datetime'] > start_date_time:
                        

                        if selection['sel_file_user_id'] in selection_user_contributions:
                            selection_user_contributions[selection['sel_file_user_id']]['contributions'] += 1
                        elif selection['sel_file_user_id'] is not None:
                            selection_user_contributions[selection['sel_file_user_id']] = {'login_id': selection['sel_file_user_login_id'], 'name': selection['sel_file_user_name'], 'contributions': 1}



                        num_selection_file_uploads += 1
                        if category_months:
                            index = axis_labels.index(selection['sel_file_upload_datetime'].date().strftime(monthly_axis_label_format))
                            selection_file_insert_list[index] += 1
                        else:
                            selection_file_insert_list[axis_labels.index(selection['sel_file_upload_datetime'].date().strftime(daily_axis_label_format))] += 1
            
            if selection['sel_file_upload_datetime'] is not None and selection['sel_file_upload_datetime'] > start_date_time:                
                if (selection['annotation'] == 'Y' or selection['annotation'] == 'M') and selection['traced'] == True:
                    traced_true_match_count += 1
                if (selection['annotation'] == 'Y' or selection['annotation'] == 'M' or selection['annotation'] == None) and selection['traced'] == False:
                    traced_true_unmatch_count += 1
                if (selection['annotation'] == 'N' or selection['annotation'] == 'M') and selection['traced'] == False:
                    traced_false_match_count += 1
                if (selection['annotation'] == 'N' or selection['annotation'] == 'M' or selection['annotation'] == None) and selection['traced'] == True:
                    traced_false_unmatch_count += 1




            if selection['contour_file_id'] is not None:
                if contour_file_valid:
                    num_contour_files += 1
                    if selection['contour_file_upload_datetime'] > start_date_time:
                        num_contour_file_uploads += 1

                        if selection['traced'] == True:
                            complete_counter += 1
                            if selection['sp_id'] not in species_complete_counter:
                                species_complete_counter[selection['sp_id']] = {'complete': 1, 'species_name': selection['species_name'], 'record':[0] * len(axis_labels)}
                            else:
                                species_complete_counter[selection['sp_id']]['complete'] += 1
                            if category_months:
                                index = axis_labels.index(selection['contour_file_upload_datetime'].date().strftime(monthly_axis_label_format))
                                species_complete_counter[selection['sp_id']]['record'][index] += 1
                            else:  
                                species_complete_counter[selection['sp_id']]['record'][axis_labels.index(selection['contour_file_upload_datetime'].date().strftime(daily_axis_label_format))] += 1


                        if selection['contour_file_user_id'] in contour_user_contributions:
                            contour_user_contributions[selection['contour_file_user_id']]['contributions'] += 1
                        elif selection['contour_file_user_id'] is not None:
                            contour_user_contributions[selection['contour_file_user_id']] = {'login_id': selection['contour_file_user_login_id'], 'name': selection['contour_file_user_name'],'contributions': 1}

                        if category_months:
                            index = axis_labels.index(selection['contour_file_upload_datetime'].date().strftime(monthly_axis_label_format))
                            contour_file_insert_list[index] += 1
                        else:
                            contour_file_insert_list[axis_labels.index(selection['contour_file_upload_datetime'].date().strftime(daily_axis_label_format))] += 1

        total_traced_count = traced_true_match_count + traced_true_unmatch_count + traced_false_match_count + traced_false_unmatch_count
        annotation_rejection_rate = round(((traced_false_unmatch_count + traced_true_unmatch_count) / total_traced_count) * 100) if total_traced_count > 0 else 0


        
        statistics_dict['speciesCompleteCounterAggregateRecord'] = []
        for species in species_complete_counter:
            total = 0
            aggregate_list = [0] * len(axis_labels)
            for i, record in enumerate(species_complete_counter[species]['record']):
                total += record
                aggregate_list[i] = total

            statistics_dict['speciesCompleteCounterAggregateRecord'].append({"label": species_complete_counter[species]['species_name'], "data": aggregate_list})

        print(statistics_dict)

        statistics_dict['completeCounter'] = complete_counter
        statistics_dict['speciesCompleteCounter'] = species_complete_counter

        statistics_dict['abandonedPlusWeekSelectionCount'] = abandoned_plus_week_selection_count
        statistics_dict['abandonedLessWeekSelectionCount'] = abandoned_less_week_selection_count

        statistics_dict['tracedTrueMatchCount'] = traced_true_match_count
        statistics_dict['tracedTrueUnmatchCount'] = traced_true_unmatch_count
        statistics_dict['tracedFalseMatchCount'] = traced_false_match_count
        statistics_dict['tracedFalseUnmatchCount'] = traced_false_unmatch_count
        statistics_dict['annotationRejectionRate'] = annotation_rejection_rate

        def sort_by_contributions(dictionary):
            return sorted(dictionary.items(), key=lambda x: x[1]['contributions'], reverse=True)

        sorted_selection_user_contributions = sort_by_contributions(selection_user_contributions)
        sorted_contour_user_contributions = sort_by_contributions(contour_user_contributions)

        statistics_dict['startDateTime'] = str(start_date_time)
        statistics_dict['endDateTime'] = str(end_date_time)
        
        statistics_dict['dayCount'] = number_days

        statistics_dict['numSelectionFiles'] = num_selection_files
        statistics_dict['numSelectionFileUploads'] = num_selection_file_uploads
        statistics_dict['numCtrFiles'] = num_contour_files
        statistics_dict['numCtrFileUploads'] = num_contour_file_uploads

        statistics_dict['selectionAndContourStatisticsChartLabels'] = axis_labels
        statistics_dict['selectionAndContourStatisticsChartData'] = []
        statistics_dict['selectionAndContourStatisticsChartData'].append({"label": "Selections Uploaded", "data": selection_file_insert_list})
        statistics_dict['selectionAndContourStatisticsChartData'].append({"label": "Contours Uploaded", "data": contour_file_insert_list})

        statistics_dict['selectionStatisticsByUserChartLabels'] = [user['name'] + " (" + user['login_id'] + ")" for user in selection_user_contributions.values()]
        statistics_dict['selectionStatisticsByUserChartData'] = [user['contributions'] for user in selection_user_contributions.values()]

        statistics_dict['contourStatisticsByUserChartLabels'] = [user['name'] + " (" + user['login_id'] + ")" for user in contour_user_contributions.values()]
        statistics_dict['contourStatisticsByUserChartData'] = [user['contributions'] for user in contour_user_contributions.values()]

        statistics_dict['selectionContributionsByUser'] = sorted_selection_user_contributions
        statistics_dict['contourContributionsByUser'] = sorted_contour_user_contributions


        return jsonify(statistics_dict)


@routes_datahub.route('/datahub/get-recording-statistics', methods=['GET'])
def get_assignment_statistics():
    recording_statistics = {'unassigned_recordings': [], 'assigned_recordings': []}

    snapshot_date=client_session.get('snapshot_date')
    snapshot_date_datetime = datetime.strptime(snapshot_date, "%Y-%m-%d %H:%M:%S.%f") if snapshot_date else None       
    if snapshot_date_datetime is None:
        snapshot_date_datetime = datetime.now()

    species_filter_str = request.args.get('species_filter')


    start_date_time = request.args.get('start_date_time')
    start_date_time = datetime.strptime(start_date_time, "%Y-%m-%dT%H:%M:%S")
    day_count = request.args.get('day_count')
    if day_count is not None and day_count.isdigit():
        start_date_time = snapshot_date_datetime - timedelta(days=int(day_count)-1)
    end_date_time = snapshot_date_datetime
    assigned_user_id = request.args.get('assigned_user_id')
    start_date_time = request.args.get('start_date_time')

    
    with Session() as session:

        records = shared_functions.get_system_time_request_recording(session, species_filter_str=species_filter_str, assigned_user_id=assigned_user_id, created_date_filter=start_date_time, override_snapshot_date=snapshot_date)
        #if user_id:
        #    user = session.query(User).filter_by(id=uuid.UUID(user_id)).first()
        #    statistics_dict['user_name'] = user.name
        #   statistics_dict['user_login_id'] = user.login_id

        number_recordings = 0
        number_assigned_recordings = 0
        number_unassigned_recordings = 0
        number_completed_assignments = 0
        number_inprogress_assignments = 0

        recordings_reviewed_count = 0
        recordings_on_hold_count = 0
        recordings_awaiting_review_count = 0
        recordings_unassigned_count = 0
        recordings_in_progress_count = 0


        all_species = session.query(Species).all()
        species_specific_data = {str(species.id): {'species_name': species.species_name, 'recordings': 0, 'assigned_recordings': 0, 'unassigned_recordings': 0, 'completed_assignments': 0, 'inprogress_assignments': 0, 'traced_count': 0, 'recordings_reviewed_count': 0, 'recordings_on_hold_count': 0, 'recordings_awaiting_review_count': 0, 'recordings_unassigned_count': 0, 'recordings_in_progress_count': 0} for species in all_species}

        completed_recordings = []
        awaiting_review_recordings = []
        on_hold_recordings = []
        assigned_recordings = []
        unassigned_recordings = []

        if assigned_user_id:
            user = session.query(User).filter_by(id=uuid.UUID(assigned_user_id)).first()
            recording_statistics['assigned_user_name'] = user.name
            recording_statistics['assigned_user_login_id'] = user.login_id
        processed_recordings = []
        for recording in records:
            recording['recording_route'] = url_for('recording.recording_view', recording_id=recording['id'], encounter_id=recording['enc_id'])
            
            
            if recording['sp_id'] in species_specific_data:
                species_specific_data[recording['sp_id']]['recordings'] += 1

                if recording['status'] == 'Reviewed':
                    completed_recordings.append(recording) if recording['id'] not in processed_recordings else None
                    species_specific_data[recording['sp_id']]['recordings_reviewed_count'] += 1 if recording['id'] not in processed_recordings else 0
                    processed_recordings.append(recording['id'])
                elif recording['status'] == 'Awaiting Review':
                    awaiting_review_recordings.append(recording) if recording['id'] not in processed_recordings else None
                    species_specific_data[recording['sp_id']]['recordings_awaiting_review_count'] += 1 if recording['id'] not in processed_recordings else 0
                    processed_recordings.append(recording['id'])
                elif recording['status'] == 'On Hold':
                    on_hold_recordings.append(recording) if recording['id'] not in processed_recordings else None
                    species_specific_data[recording['sp_id']]['recordings_on_hold_count'] += 1 if recording['id'] not in processed_recordings else 0
                    processed_recordings.append(recording['id'])
                elif recording['status'] == 'Unassigned':
                    unassigned_recordings.append(recording)
                    species_specific_data[recording['sp_id']]['recordings_unassigned_count'] += 1
                elif recording['status'] == 'In Progress':
                    assigned_recordings.append(recording)
                    species_specific_data[recording['sp_id']]['recordings_in_progress_count'] += 1 if recording['id'] not in processed_recordings else 0
                    processed_recordings.append(recording['id'])

                if recording['assignment_user_login_id'] is not None:

                    species_specific_data[recording['sp_id']]['assigned_recordings'] += 1
                    if recording['assignment_completed_flag'] == True:
                        species_specific_data[recording['sp_id']]['completed_assignments'] += 1
                    elif recording['assignment_completed_flag'] == False:
                        species_specific_data[recording['sp_id']]['inprogress_assignments'] += 1
                else: 
                    species_specific_data[recording['sp_id']]['unassigned_recordings'] += 1
                species_specific_data[recording['sp_id']]['traced_count'] += recording['traced_count']

        recording_statistics['unassigned_recordings'] = sorted(unassigned_recordings, key=lambda x: x['created_datetime'], reverse=True)
        
        recording_statistics['on_hold_recordings'] = sorted(on_hold_recordings, key=lambda x: x['created_datetime'], reverse=True)
        
        recording_statistics['awaiting_review_recordings'] = sorted(awaiting_review_recordings, key=lambda x: x['created_datetime'], reverse=True)
        recording_statistics['completed_recordings'] = sorted(completed_recordings, key=lambda x: x['created_datetime'], reverse=True)
        recording_statistics['assigned_recordings'] = sorted(assigned_recordings, key=lambda x: (-(x['traced_count']==0 and x['assignment_completed_flag']==True), x['assignment_completed_flag'], x['created_datetime']))
        for sp_id in species_specific_data:
            species_specific_data[sp_id]['completion_rate'] = round((species_specific_data[sp_id]['completed_assignments'] / species_specific_data[sp_id]['assigned_recordings']) * 100, 0) if species_specific_data[sp_id]['recordings'] > 0 else 0

            species_specific_data[sp_id]['recordings_count'] = species_specific_data[sp_id]['recordings_unassigned_count'] + species_specific_data[sp_id]['recordings_in_progress_count'] + species_specific_data[sp_id]['recordings_reviewed_count'] + species_specific_data[sp_id]['recordings_awaiting_review_count'] + species_specific_data[sp_id]['recordings_on_hold_count']
            species_specific_data[sp_id]['progress'] = round((species_specific_data[sp_id]['recordings_reviewed_count'] / species_specific_data[sp_id]['recordings_count']) * 100, 0) if species_specific_data[sp_id]['recordings_count'] > 0 else 0


        return jsonify(species_statistics=species_specific_data, recording_statistics=recording_statistics)