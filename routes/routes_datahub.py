# Third-party imports
from flask import Blueprint, Response, flash,get_flashed_messages, jsonify, redirect,render_template,request, send_file,session, url_for, send_from_directory
from sqlalchemy.orm import joinedload,sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from flask_login import login_user,login_required, current_user, login_manager

# Local application imports
from db import FILE_SPACE_PATH, Session, GOOGLE_API_KEY, parse_alchemy_error, save_snapshot_date_to_session,require_live_session,exclude_role_1,exclude_role_2,exclude_role_3,exclude_role_4
from models import *
import exception_handler

routes_datahub = Blueprint('datahub', __name__)


@routes_datahub.route('/datahub', methods=['GET'])
@login_required
def datahub_view():
    with Session() as session:
        return render_template('datahub/datahub.html')


@routes_datahub.route('/datahub/get-selection-statistics', methods=['GET'])
def get_selection_statistics():
    data = request.args.get('data')  # Get the data from the query parameters
    print(data)
    with Session() as session:
        return jsonify(selections=session.query(Selection).count())
    

@routes_datahub.route('/datahub/get-number-new-selections', methods=['GET'])
def get_number_new_selections():
    data_response = {'numSelections':0,'ctrFileUploads': 0, 'selFileUploads': 0, 'traceSuccessRate': 0, 'numAnnotationsY': 0, 'numAnnotationsN': 0, 'numAnnotationsM': 0, 'numAnnotationsNone': 0}
    
    number_of_selections = 0
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    with Session() as session:
        selections = shared_functions.create_system_time_between_request(session, Selection, start_date, end_date, order_by="id,row_start")

        prev_selection = selections[0]
        traced = False
        annotation = "X"
        for selection in selections:
            if selection['id'] != prev_selection['id']:
                data_response['numSelections'] += 1
                if annotation == "Y":
                    data_response['numAnnotationsY'] += 1
                elif annotation == "N":
                    data_response['numAnnotationsN'] += 1
                elif annotation == "M":
                    data_response['numAnnotationsM'] += 1
                elif annotation == None:
                    data_response['numAnnotationsNone'] += 1
                annotation = "X"
            else:
                print("I got here")
                if prev_selection['ctr_file_id'] == None and selection['ctr_file_id'] != None:
                    data_response['ctrFileUploads'] += 1
                if prev_selection['selection_file_id'] == None and selection['selection_file_id'] != None:
                    data_response['selFileUploads'] += 1
                annotation=selection['annotation']
                print(annotation)
            prev_selection = selection




        return jsonify(data_response)