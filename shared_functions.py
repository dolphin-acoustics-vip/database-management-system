from datetime import datetime
import uuid
from flask import session as client_session
from flask import redirect, url_for, render_template, request
from db import db
import exception_handler
from flask_login import login_user,login_required, current_user, login_manager


def get_system_time_request_recording(session, user_id=None, assigned_user_id=None, created_date_filter=None, species_filter_str=None, override_snapshot_date=None):
    from models import Recording
    snapshot_date=client_session.get('snapshot_date') if override_snapshot_date is None else override_snapshot_date

    columns = "rec.id, rec.created_datetime, rec.start_time, rec.status, enc.id enc_id, enc.encounter_name enc_encounter_name, enc.location enc_location, sp.id sp_id, sp.species_name sp_species_name, assignment.created_datetime assignment_created_datetime, assignment.completed_flag assignment_completed_flag, COUNT(sel.id) traced_count, assignment_user.id assignment_user_id, assignment_user.name assignment_user_name, assignment_user.login_id assignment_user_login_id"
    joins = "LEFT JOIN encounter AS enc ON rec.encounter_id = enc.id LEFT JOIN species AS sp ON enc.species_id = sp.id LEFT JOIN assignment ON rec.id = assignment.recording_id LEFT JOIN user AS assignment_user ON assignment.user_id = assignment_user.id LEFT JOIN selection AS sel ON rec.id = sel.recording_id AND sel.traced = 1"

    if snapshot_date: query_str="SELECT {} FROM {} FOR SYSTEM_TIME AS OF '{}' AS sel".format(columns, Recording.__tablename__, snapshot_date)
    else: query_str="SELECT {} FROM {} AS rec".format(columns, Recording.__tablename__)
    query_str += " {}".format(joins)
    next_clause = "WHERE"
    if assigned_user_id:
        query_str += " {} assignment.user_id = '{}'".format(next_clause, assigned_user_id)
        next_clause = "AND"
    if created_date_filter:
        query_str += " {} rec.created_datetime >= '{}'".format(next_clause, created_date_filter)
        next_clause = "AND"
    if species_filter_str is not None and species_filter_str != '':
        species_filter = species_filter_str.split(",")
        species_filter_str = ", ".join("'" + item + "'" for item in species_filter)
        query_str += " {} sp.id IN ({})".format(next_clause, species_filter_str)

    query_str += " GROUP BY rec.id, rec.start_time, enc.id, enc.encounter_name, enc.location, sp.id, sp.species_name, assignment.created_datetime, assignment.completed_flag"

    query = db.text(query_str)
    print(query)
    result = session.execute(query)
    # Fetch all results
    records_raw = result.fetchall()
    # Create a list of dictionaries with column names as keys
    records = [{column: value for column, value in zip(result.keys(), record)} for record in records_raw]
    
    return records

def get_system_time_request_with_joins(session, user_id=None, assigned_user_id=None, created_date_filter=None, species_filter_str=None, override_snapshot_date=None):
    from models import Selection
    
    
    snapshot_date=client_session.get('snapshot_date') if override_snapshot_date is None else override_snapshot_date

    columns = "sel.id, sel.row_start sel_row_start, sel.created_datetime sel_created_datetime, sel.selection_number, sel.row_start, sel.row_end, sel.selection_file_id, sel.contour_file_id, sel.annotation, sel.traced, sel.updated_by_id sel_updated_by_id, sel_file.filename sel_file_filename, sel_file.upload_datetime sel_file_upload_datetime, sel_file.updated_by_id sel_file_updated_by_id, contour_file.filename contour_file_filename, contour_file.upload_datetime contour_file_upload_datetime, contour_file.updated_by_id contour_file_updated_by_id, sel_file_user.id sel_file_user_id, sel_file_user.login_id sel_file_user_login_id, sel_file_user.name sel_file_user_name, contour_file_user.id contour_file_user_id, contour_file_user.name contour_file_user_name, contour_file_user.login_id contour_file_user_login_id, sp.id sp_id, sp.species_name species_name, rec.id rec_id, rec.start_time rec_start_time, enc.id enc_id, enc.encounter_name enc_encounter_name, enc.location enc_location"
    joins = "LEFT JOIN file AS sel_file ON sel_file.id = sel.selection_file_id LEFT JOIN file AS contour_file ON contour_file.id = sel.contour_file_id LEFT JOIN user AS sel_file_user ON sel_file.updated_by_id = sel_file_user.id LEFT JOIN user AS contour_file_user ON contour_file.updated_by_id = contour_file_user.id LEFT JOIN recording AS rec ON sel.recording_id = rec.id LEFT JOIN encounter AS enc ON rec.encounter_id = enc.id LEFT JOIN species AS sp ON enc.species_id = sp.id LEFT JOIN assignment ON rec.id = assignment.recording_id"
    
    if snapshot_date: query_str="SELECT {} FROM {} FOR SYSTEM_TIME AS OF '{}' AS sel".format(columns, Selection.__tablename__, snapshot_date)
    else: query_str="SELECT {} FROM {} AS sel".format(columns, Selection.__tablename__)
    query_str += " {}".format(joins)
    next_clause = "WHERE"
    if user_id: 
        query_str += " WHERE sel_file.updated_by_id = '{}' OR contour_file.updated_by_id = '{}' OR sel.updated_by_id = '{}'".format(user_id, user_id, user_id)
        next_clause = "AND"
    if assigned_user_id: 
        query_str += " {} assignment.user_id = '{}'".format(next_clause, assigned_user_id)
        next_clause = "AND"
    if created_date_filter:
        query_str += " {} sel.created_datetime >= '{}'".format(next_clause, created_date_filter)
        next_clause = "AND"
    if species_filter_str is not None and species_filter_str != '':
        species_filter = species_filter_str.split(",")
        species_filter_str = ", ".join("'" + item + "'" for item in species_filter)
        query_str += " {} sp.id IN ({})".format(next_clause, species_filter_str)
    query = db.text(query_str)
    print(query)
    result = session.execute(query)
    # Fetch all results
    records_raw = result.fetchall()
    # Create a list of dictionaries with column names as keys
    records = [{column: value for column, value in zip(result.keys(), record)} for record in records_raw]
    
    return records


def page_not_found(error,redirect):
    snapshot_date = client_session.get('snapshot_date')
    return render_template('error.html', error_code=404, error=error, goback_link=redirect, goback_message="Home", snapshot_date=snapshot_date, user=current_user)

def create_system_time_between_request(session, db_object, start_date, end_date, filters=None, order_by=None):
    from models import User

    query_str="SELECT *,row_start,row_end FROM {} FOR SYSTEM_TIME BETWEEN '{}' AND '{}'".format(db_object.__tablename__, start_date, end_date)
    if filters:
        filter_str = " AND ".join(["{} = '{}'".format(key, value) for key, value in filters.items()])
        query_str += " WHERE " + filter_str

    if order_by:
        query_str += " ORDER BY " + order_by

    
    query = db.text(query_str)
    print(query)
    result = session.execute(query)
    
    # Fetch all results
    records = result.fetchall()

    # Create a list of dictionaries with column names as keys
    recording_history = [{column: value for column, value in zip(result.keys(), record)} for record in records]

    for recording_history_item in recording_history:
        if recording_history_item['updated_by_id'] is not None and recording_history_item['updated_by_id'].strip() != "":
            recording_history_item['updated_by'] = session.query(User).filter_by(id=uuid.UUID(recording_history_item['updated_by_id'])).first()  
        else:
            recording_history_item['updated_by'] = None 
    # Sort the data by 'row_start' dates
    recording_history.sort(key=lambda x: x['row_start'])
    


    return recording_history


def create_system_time_request(session, db_object, filters=None, order_by=None,override_snapshot_date=None, one_result=False):
    snapshot_date=client_session.get('snapshot_date') if override_snapshot_date is None else override_snapshot_date
    if snapshot_date: query_str="SELECT * FROM {} FOR SYSTEM_TIME AS OF '{}'".format(db_object.__tablename__, snapshot_date)
    else: query_str="SELECT * FROM {}".format(db_object.__tablename__)
    if filters:
        filter_str = " AND ".join(["{} = '{}'".format(key, value) for key, value in filters.items()])
        query_str += " WHERE " + filter_str

    if order_by:
        query_str += " ORDER BY " + order_by

    query = db.text(query_str)
    queried_db_object = session.query(db_object).from_statement(query).all()
    if one_result:
        try:
            queried_db_object = queried_db_object[0]
        except Exception as e:
            raise exception_handler.NotFoundException(f"{db_object.__tablename__} not found")

    return queried_db_object



def create_all_time_request(session, db_object, filters=None, order_by=None):
    from models import User
    # Write the raw SQL query to select all records from the recording table for all system time versions
    # Execute the raw SQL query with the recording_id parameter
    
    query_str="SELECT *,row_start FROM {} FOR SYSTEM_TIME ALL".format(db_object.__tablename__)
    
    if filters:
        filter_str = " AND ".join(["{} = '{}'".format(key, value) for key, value in filters.items()])
        query_str += " WHERE " + filter_str

    if order_by:
        query_str += " ORDER BY " + order_by
    
    query = db.text(query_str)
    
    result = session.execute(query)
    
    # Fetch all results
    records = result.fetchall()

    # Create a list of dictionaries with column names as keys
    recording_history = [{column: value for column, value in zip(result.keys(), record)} for record in records]

    for recording_history_item in recording_history:
        if recording_history_item['updated_by_id'] is not None and recording_history_item['updated_by_id'].strip() != "":
            recording_history_item['updated_by'] = session.query(User).filter_by(id=uuid.UUID(recording_history_item['updated_by_id'])).first()  
        else:
            recording_history_item['updated_by'] = None 
    # Sort the data by 'row_start' dates
    recording_history.sort(key=lambda x: x['row_start'])
    


    def parse_value(key, value, prev_value):
        return_string = ""
        if type(value) == datetime or type(prev_value) == datetime:
            return_string = 'UPDATE ' + key + ' ' + str(value)
        else:
            try:
                value = uuid.UUID(value) if value else None
                prev_value = uuid.UUID(prev_value) if prev_value else None
                
                if value and prev_value == None:
                    return_string = 'ADD ' + key
                elif value == None and prev_value:
                    return_string = 'DELETE ' + key
                elif value and prev_value:
                    return_string = 'UPDATE ' + key
                else:
                    return_string="TEST"
            except (ValueError,AttributeError):
                return_string = 'UPDATE ' + key + ' -> ' + str(value)


        
        return return_string
    prev_element = None
    for element in recording_history:
        if prev_element is None:
            element['action'] = 'CREATE'
        else:
            changes = [parse_value(key, element[key], prev_element[key]) for key in element if element[key] != prev_element.get(key) and key not in ['row_start', 'updated_by_id', 'updated_by']]
            element['action'] = changes if changes else 'No changes'
        prev_element = element
    #missing_selections, error_msg = recording.validate_selection_table(session)
    #missing_selections=[]
    #error_msg=""

    return recording_history
