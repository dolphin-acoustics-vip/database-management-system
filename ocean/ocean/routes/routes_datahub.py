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
from datetime import datetime, timedelta

# Third-party imports
from flask import Blueprint, Response, flash,get_flashed_messages, json, jsonify, redirect,render_template,request, send_file,session, url_for, send_from_directory
from sqlalchemy.orm import joinedload,sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from flask_login import login_user,login_required, current_user, login_manager
from flask import session as client_session

# Local application imports
import ocean.database_handler as database_handler
import ocean.models as models

routes_datahub = Blueprint('datahub', __name__)

@routes_datahub.route('/datahub', methods=['GET'])
@login_required
@database_handler.exclude_role_3
@database_handler.exclude_role_4
def datahub_view():
    with database_handler.get_session() as session:
        species_list = session.query(models.Species).all()
        return render_template('datahub/datahub.html', species_list=species_list)



# Used for graphs
daily_axis_label_format = "%d %b %Y"
monthly_axis_label_format = "%b %Y"

def create_date_axis_labels(start_date: datetime, end_date: datetime) -> tuple:
    """
    Generate date axis labels based on the given start and end dates.
    If the range is greater than 90 days the axis labels are categorised by months
    in ascending order. Otherwise they are categorised by daily dates in ascending order

    :param start_date: The start date of the date range.
    :param end_date: The end date of the date range.
    
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


@routes_datahub.route('/datahub/get-selection-statistics', methods=['GET'])
@login_required
@database_handler.exclude_role_3
@database_handler.exclude_role_4
def get_selection_statistics():

    """
    Retrieves statistics for the data hub based on the provided parameters.

    Request parameters:
        - species_filter (list): A list of species ids to filter the statistics by (can be empty if no filter).
        - dayCount (int): The number of days to retrieve statistics for.
        - start_date_time (str): The start date and time for the statistics in yyyy-mm-ddTHH:MM:SS format (if a dayCount is given this can be left blank)
        - user_id (str): The user ID if the statistics are to be filtered for a single user (can be empty if no filter).

    Returns:
        A JSON object containing selection statistics (see code for more detail on JSON format and how the calculations are made)
    """
    statistics_dict = {
        
    }

    # Snapshot date limits the statistics to be retrieved to a certain point in history (or now if None).
    snapshot_date=client_session.get('snapshot_date')
    snapshot_date_datetime = database_handler.parse_snapshot_date(snapshot_date) if snapshot_date else None
    if snapshot_date_datetime is None:
        snapshot_date_datetime = datetime.now()

    # Species and user filter.
    species_filter_str = request.args.get('species_filter')
    user_id = request.args.get('user_id')
    # Determine the period for which the statistics should be retrieved.
    start_date_time = request.args.get('start_date_time')
    start_date_time = datetime.strptime(start_date_time, "%Y-%m-%dT%H:%M:%S")
    dayCount = request.args.get('dayCount')
    if dayCount is not None and dayCount.isdigit():
        start_date_time = snapshot_date_datetime - timedelta(days=int(dayCount)-1)
    end_date_time = snapshot_date_datetime

    with database_handler.get_session() as session:
        records = database_handler.get_system_time_request_selection(session, user_id=user_id, species_filter_str=species_filter_str, override_snapshot_date=snapshot_date)
        
        # Grab user filter information which is returned in the statistics (for informational purposes)
        if user_id:
            user = session.query(models.User).filter_by(id=user_id).first()
            if user:
                statistics_dict['userName'] = user.name
                statistics_dict['userLoginId'] = user.login_id
    
        start_date = start_date_time.date()
        end_date = end_date_time.date()
        number_days = (int((end_date - start_date).days) + 1)

        statistics_dict['startDateTime'] = str(start_date_time)
        statistics_dict['endDateTime'] = str(end_date_time)
        statistics_dict['dayCount'] = number_days

        num_selection_files = 0 # total number of selection files (all time)
        num_selection_file_uploads = 0 # total number of selection files (between start and end date)
        num_contour_files = 0 # total number of contour files (all time)
        num_contour_file_uploads = 0 # total number of contour files (between start and end date)
       
        # Create data used to render a chart of selection file and contour file uploads over time
        # selection_file_insert_list and contour_file_insert_list are lists of length number_days
        # as they will contain y-axis values for each x-axis element in axis_labels.
        axis_labels, category_months = create_date_axis_labels(start_date, end_date)
        selection_file_insert_list = [0] * len(axis_labels)
        contour_file_insert_list = [0] * len(axis_labels)

        # Create a dictionary of species names to store a number of statistics for each
        species_statistics = {}

        # Calculate a number of selection and contour file uploads for each user
        selection_user_contributions = {}
        contour_user_contributions = {}

        # These statistics are not sent to the frontend but are used in an intermediary step to calculate the annotation rejection rate
        traced_true_matchCount = 0 # the number of times Selection.traced is true and annotation is Y or M
        traced_true_unmatchCount = 0 # the number of times Selection.traced is true and annotation is N
        traced_false_matchCount = 0 # the number of times Selection.traced is false and annotation is N or M
        traced_false_unmatchCount = 0 # the number of times Selection.traced is false and annotation is Y

        for selection in records:

            # Per-species calculations
            if selection['sp_id'] not in species_statistics:
                # Add new species to the dictionary
                # - untracedCount is the number of selections in that species that have not been traced
                # - deactivatedCount is the number of selections in that species that have been deactivated
                # - completedCount is the number of selections in that species that have been traced and are complete
                # - record is used to populate a line graph (where we need to know selection traces over an axis time).
                #   It is a list of length number_days as it will contain y-axis values for each x-axis element in axis_labels
                species_statistics[selection['sp_id']] = {
                    'untracedCount':0,
                    'deactivatedCount':0,
                    'completedCount': 0,
                    'speciesName': selection['species_name'],
                    'record':[0] * len(axis_labels)}
            if selection['deactivated'] == True:
                species_statistics[selection['sp_id']]['deactivatedCount'] += 1
            else:
                if selection['traced'] == True:
                    species_statistics[selection['sp_id']]['completedCount'] += 1
                    if category_months:
                        index = axis_labels.index(selection['contour_file_upload_datetime'].date().strftime(monthly_axis_label_format))
                        species_statistics[selection['sp_id']]['record'][index] += 1
                    else:  
                        species_statistics[selection['sp_id']]['record'][axis_labels.index(selection['contour_file_upload_datetime'].date().strftime(daily_axis_label_format))] += 1
                elif selection['traced'] == None:
                    species_statistics[selection['sp_id']]['untracedCount'] += 1

            # Selection file stats
            if selection['selection_file_id'] is not None:
                # Check if the selection file was uploaded by the user filter (or just continue if no user filter given)
                if not user_id or user_id and selection['sel_file_updated_by_id'] == user_id:
                    num_selection_files += 1
                    # Check if the selection file was uploaded after the defined start date filter
                    if selection['sel_file_upload_datetime'] > start_date_time:
                        num_selection_file_uploads += 1
                        # Count user-specific selection contributions in the dictionary (see definition above)
                        if selection['sel_file_user_id'] in selection_user_contributions:
                            selection_user_contributions[selection['sel_file_user_id']]['contributions'] += 1
                        elif selection['sel_file_user_id'] is not None:
                            selection_user_contributions[selection['sel_file_user_id']] = {'login_id': selection['sel_file_user_login_id'], 'name': selection['sel_file_user_name'], 'contributions': 1}
                        # Add selection file upload data to the chart for a particular month or date
                        if category_months:
                            index = axis_labels.index(selection['sel_file_upload_datetime'].date().strftime(monthly_axis_label_format))
                            selection_file_insert_list[index] += 1
                        else:
                            selection_file_insert_list[axis_labels.index(selection['sel_file_upload_datetime'].date().strftime(daily_axis_label_format))] += 1
            
            # Annotation rejection rate calculations
            if selection['sel_file_upload_datetime'] is not None and selection['sel_file_upload_datetime'] > start_date_time:                
                if (selection['annotation'] == 'Y' or selection['annotation'] == 'M') and selection['traced'] == True:
                    traced_true_matchCount += 1
                if (selection['annotation'] == 'Y' or selection['annotation'] == 'M' or selection['annotation'] == None) and selection['traced'] == False:
                    traced_true_unmatchCount += 1
                if (selection['annotation'] == 'N' or selection['annotation'] == 'M') and selection['traced'] == False:
                    traced_false_matchCount += 1
                if (selection['annotation'] == 'N' or selection['annotation'] == 'M' or selection['annotation'] == None) and selection['traced'] == True:
                    traced_false_unmatchCount += 1


            if selection['contour_file_id'] is not None:
                # Check if the contour file was uploaded by the user filter (or just continue if no user filter given)
                if not user_id or user_id and selection['contour_file_updated_by_id'] == user_id:
                    num_contour_files += 1
                    # Check if the contour file was uploaded after the defined start date filter
                    if selection['contour_file_upload_datetime'] > start_date_time:
                        num_contour_file_uploads += 1
                        # Count user-specific contour contributions in the dictionary (see definition above)
                        if selection['contour_file_user_id'] in contour_user_contributions:
                            contour_user_contributions[selection['contour_file_user_id']]['contributions'] += 1
                        elif selection['contour_file_user_id'] is not None:
                            contour_user_contributions[selection['contour_file_user_id']] = {'login_id': selection['contour_file_user_login_id'], 'name': selection['contour_file_user_name'],'contributions': 1}
                        # Add contour file upload data to the chart for a particular month or date
                        if category_months:
                            index = axis_labels.index(selection['contour_file_upload_datetime'].date().strftime(monthly_axis_label_format))
                            contour_file_insert_list[index] += 1
                        else:
                            contour_file_insert_list[axis_labels.index(selection['contour_file_upload_datetime'].date().strftime(daily_axis_label_format))] += 1

        # Counting the percentage of selections where the user has rejected an annotation
        total_tracedCount = traced_true_matchCount + traced_true_unmatchCount + traced_false_matchCount + traced_false_unmatchCount
        annotation_rejection_rate = round(((traced_false_unmatchCount + traced_true_unmatchCount) / total_tracedCount) * 100) if total_tracedCount > 0 else 0
        statistics_dict['annotationRejectionRate'] = annotation_rejection_rate

        # Summarising the statistics for selection traces over time (aggregate - shown as a line graph)
        # See above for the meaning of species_statistics[species]['record']. By looping through
        # and adding to an aggregate total we send an array of values to be plotted on an aggregate line
        # graph to the client.
        statistics_dict['speciesStatistics'] = species_statistics
        statistics_dict['speciesStatisticsAggregateTraced'] = []
        for species in species_statistics:
            total = 0
            aggregate_list = [0] * len(axis_labels)
            for i, record in enumerate(species_statistics[species]['record']):
                total += record
                aggregate_list[i] = total
            statistics_dict['speciesStatisticsAggregateTraced'].append({"label": species_statistics[species]['speciesName'], "data": aggregate_list})

        def sort_by_contributions(dictionary):
            return sorted(dictionary.items(), key=lambda x: x[1]['contributions'], reverse=True)
        sorted_selection_user_contributions = sort_by_contributions(selection_user_contributions)
        sorted_contour_user_contributions = sort_by_contributions(contour_user_contributions)

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
@login_required
@database_handler.exclude_role_3
@database_handler.exclude_role_4
def get_recording_statistics():
    recording_statistics = {'unassignedRecordings': [], 'assignedRecordings': []}

    snapshot_date=client_session.get('snapshot_date')
    snapshot_date_datetime = datetime.strptime(snapshot_date, "%Y-%m-%d %H:%M:%S.%f") if snapshot_date else None       
    if snapshot_date_datetime is None:
        snapshot_date_datetime = datetime.now()

    # Filter information passed as parameter to web request
    species_filter_str = request.args.get('species_filter')
    assigned_user_id = request.args.get('assigned_user_id')
    start_date_time = request.args.get('start_date_time')
    start_date_time = datetime.strptime(start_date_time, "%Y-%m-%dT%H:%M:%S")
    dayCount = request.args.get('dayCount')
    if dayCount is not None and dayCount.isdigit():
        start_date_time = snapshot_date_datetime - timedelta(days=int(dayCount)-1)

    with database_handler.get_session() as session:
        records = database_handler.get_system_time_request_recording(session, species_filter_str=species_filter_str, assigned_user_id=assigned_user_id, created_date_filter=start_date_time, override_snapshot_date=snapshot_date)
        all_species = database_handler.create_system_time_request(session, models.Species)

        # Dictionary to store recording statistics for each species
        species_specific_data = {str(species.id): {'speciesName': species.species_name, 'recordings': 0, 'assignedRecordings': 0, 'unassignedRecordings': 0, 'completedAssignments': 0, 'inprogressAssignments': 0, 'tracedCount': 0, 'recordingsReviewedCount': 0, 'recordingsOnHoldCount': 0, 'recordingsAwaitingReviewCount': 0, 'recordingsUnassignedCount': 0, 'recordingsInProgressCount': 0} for species in all_species}

        # Variables to store recordings statistics depending on each of its status (a field containing either
        # Reviewed, Awaiting Review, In Hold, Unassigned, In Progress)
        completedRecordings = []
        awaitingReviewRecordings = []
        onHoldRecordings = []
        assignedRecordings = []
        unassignedRecordings = []

        if assigned_user_id:
            user = session.query(models.User).filter_by(id=assigned_user_id).first()
            if user:
                recording_statistics['assignedUserName'] = user.name
                recording_statistics['assignedUserLoginId'] = user.login_id
            

        processed_recordings = [] # keep track of recordings that have already been processed as to not duplicate their stats
        for recording in records:
            # Route for a button to access the recording in the front end
            recording['recordingRoute'] = url_for('recording.recording_view', recording_id=recording['id'], encounter_id=recording['enc_id'])
            # Add statistics for recording to its corresponding species entry in species_specific_data
            if recording['sp_id'] in species_specific_data:
                species_specific_data[recording['sp_id']]['recordings'] += 1
                if recording['status'] == 'Reviewed':
                    completedRecordings.append(recording) if recording['id'] not in processed_recordings else None
                    species_specific_data[recording['sp_id']]['recordingsReviewedCount'] += 1 if recording['id'] not in processed_recordings else 0
                    processed_recordings.append(recording['id'])
                elif recording['status'] == 'Awaiting Review':
                    awaitingReviewRecordings.append(recording) if recording['id'] not in processed_recordings else None
                    species_specific_data[recording['sp_id']]['recordingsAwaitingReviewCount'] += 1 if recording['id'] not in processed_recordings else 0
                    processed_recordings.append(recording['id'])
                elif recording['status'] == 'On Hold':
                    onHoldRecordings.append(recording) if recording['id'] not in processed_recordings else None
                    species_specific_data[recording['sp_id']]['recordingsOnHoldCount'] += 1 if recording['id'] not in processed_recordings else 0
                    processed_recordings.append(recording['id'])
                elif recording['status'] == 'Unassigned':
                    unassignedRecordings.append(recording)
                    species_specific_data[recording['sp_id']]['recordingsUnassignedCount'] += 1
                elif recording['status'] == 'In Progress':
                    assignedRecordings.append(recording)
                    species_specific_data[recording['sp_id']]['recordingsInProgressCount'] += 1 if recording['id'] not in processed_recordings else 0
                    processed_recordings.append(recording['id'])
                # Count total number of recordings that have been assigned, completed, are unassigned, or are currently in progress
                if recording['assignment_user_login_id'] is not None:
                    species_specific_data[recording['sp_id']]['assignedRecordings'] += 1
                    if recording['assignment_completed_flag'] == True:
                        species_specific_data[recording['sp_id']]['completedAssignments'] += 1
                    elif recording['assignment_completed_flag'] == False:
                        species_specific_data[recording['sp_id']]['inprogressAssignments'] += 1
                else: 
                    species_specific_data[recording['sp_id']]['unassignedRecordings'] += 1
                # Count total number of selections that have been traced for each recording (traced_count must be generated in the query)
                species_specific_data[recording['sp_id']]['tracedCount'] += recording['traced_count']

        recording_statistics['unassignedRecordings'] = sorted(unassignedRecordings, key=lambda x: x['created_datetime'], reverse=True)
        recording_statistics['onHoldRecordings'] = sorted(onHoldRecordings, key=lambda x: x['created_datetime'], reverse=True)
        recording_statistics['awaitingReviewRecordings'] = sorted(awaitingReviewRecordings, key=lambda x: x['created_datetime'], reverse=True)
        recording_statistics['completedRecordings'] = sorted(completedRecordings, key=lambda x: x['created_datetime'], reverse=True)
        recording_statistics['assignedRecordings'] = sorted(assignedRecordings, key=lambda x: (-(x['traced_count']==0 and x['assignment_completed_flag']==True), x['assignment_completed_flag'], x['created_datetime']))
        
        for species_id in species_specific_data:
            species_specific_data[species_id]['completionRate'] = round((species_specific_data[species_id]['completedAssignments'] / species_specific_data[species_id]['assignedRecordings']) * 100, 0) if species_specific_data[species_id]['assignedRecordings'] > 0 else 0
            species_specific_data[species_id]['recordingsCount'] = species_specific_data[species_id]['recordingsUnassignedCount'] + species_specific_data[species_id]['recordingsInProgressCount'] + species_specific_data[species_id]['recordingsReviewedCount'] + species_specific_data[species_id]['recordingsAwaitingReviewCount'] + species_specific_data[species_id]['recordingsOnHoldCount']
            species_specific_data[species_id]['progress'] = round((species_specific_data[species_id]['recordingsReviewedCount'] / species_specific_data[species_id]['recordingsCount']) * 100, 0) if species_specific_data[species_id]['recordingsCount'] > 0 else 0


        return jsonify(species_statistics=species_specific_data, recording_statistics=recording_statistics)