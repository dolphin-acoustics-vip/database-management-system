from datetime import datetime
import uuid
from flask import session as client_session
from flask import redirect, url_for, render_template, request
from db import db
import exception_handler
from flask_login import login_user,login_required, current_user, login_manager




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
