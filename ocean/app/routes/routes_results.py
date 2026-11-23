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
from flask import Blueprint, flash, render_template, redirect, request, session as client_session, url_for
from flask_login import login_required, current_user
from datetime import datetime, timedelta

# Local application imports
from .. import database_handler
from .. import models

# Local application imports
from .. import database_handler
from .. import models
from .. import exception_handler
from .. import utils
from .. import response_handler
from .. import transaction_handler
from ..logger import logger

routes_results = Blueprint('results', __name__)

@routes_results.route("/results", methods = ["GET"])
@login_required
def results():
    """GET route to show the page with a list of all results."""
    
    with database_handler.get_session() as session:
        from ..models import File
        File.get_abandoned_files(session)
        try:
            results_list = database_handler.create_system_time_request(session, models.Job, {}, order_by="upload_datetime DESC")
            return render_template('results/results.html', results_list=results_list)
        except Exception as e:
            exception_handler.handle_exception(exception=e, session=session)
            return redirect(url_for('general.home'))

@routes_results.route("/results/new", methods = ["GET"])
@login_required
@database_handler.exclude_role_3
@database_handler.exclude_role_4
@database_handler.require_live_session
def results_new():
    """GET route to show the page to add a new result."""
    
    return render_template('results/results-new.html')

def parse_file(request):
    if 'output_file' not in request.files or request.files['output_file'].filename == '':
        raise exception_handler.WarningException("No output file provided.")
    upload = request.files['output_file']
    if not (upload.filename.endswith(".mat") or upload.filename.endswith(".json")):
        raise exception_handler.WarningException("Output file must be a .mat or .json file.")
    parsed_output = utils.parse_ARTWarp_Output(upload)
    file_stream = utils.toJSON(parsed_output)
    return parsed_output, file_stream

def insert_job(session, user, form):
    job = models.Job()
    job.insert(form)
    job.user = user
    session.add(job)
    session.flush()
    return job

def insert_categories(session, job, parsed_output):
    # Create categories associated with job
    for i in range(parsed_output["summary"]["num_categories"]):
        category = models.Category()
        form = {"job": job, "category_number": i}
        category.insert(form)
        session.add(category)
    session.flush()

def insert_reference_contours(session, transaction, job, parsed_output):
    # Create all associated reference contours
    for i in range(parsed_output["summary"]["num_categories"]):
        reference_contour = models.Reference_Contour()
        category = database_handler.create_system_time_request(session, models.Category, filters={"job_id":job.id, "category_number": i}, one_result=True)
        form = {"category": category}
        
        reference_contour.insert(form)
        session.add(reference_contour)
        session.flush()
        
        contour_file = transaction.create_tracked_file()
        ctr_file = transaction.create_tracked_file()
        reference_contour.parse_contour_data(
            parsed_output["categories"][str(i)]["reference_contour"],
            contour_file, ctr_file)

        contour = models.Contour()
        contour.insert({"category": category, "reference_contour": reference_contour})

        session.add(contour)
    session.flush()

def insert_contours(session, job, parsed_output):
    # Create all contours for a category linking to a selection
    for contour_data in parsed_output["contours"].values():
        category_num = contour_data["category_num"]
        original_filename = contour_data["name"]

        contour = models.Contour()

        category = database_handler.create_system_time_request(session, models.Category, filters={"job_id": job.id, "category_number": category_num}, one_result=True)

        # CHECK not sure if this is the best way to link the contour file to 
        contour_file = database_handler.create_system_time_request(session, models.File, filters={"original_filename": original_filename}, one_result=True)
        selection = database_handler.create_system_time_request(session, models.Selection, filters={"contour_file_id": contour_file.id}, one_result=True)
        if not selection:
            raise exception_handler.WarningException("Could not connect contour to selection.")
        else:
            contour.insert({"category": category, "selection": selection})
            session.add(contour)
    session.flush()

@routes_results.route('/results/insert/', methods=['POST'])
@login_required
@database_handler.exclude_role_3
@database_handler.exclude_role_4
@database_handler.require_live_session
def results_insert():
    with response_handler.json_response_context() as response:
        with transaction_handler.atomic_with_filespace() as transaction:
            session = transaction.session

            parsed_output, file_stream = parse_file(request)

            user = database_handler.create_system_time_request(session, models.User, filters={"id":current_user.id}, one_result=True)

            job = insert_job(session, user, request.form)

            output_file = transaction.create_tracked_file()
            output_file.insert(file_stream, job.relative_directory, job.complete_output_filename, extension="json")
            job.complete_output_file_insert(output_file)
            job.parse_network_paremeters(parsed_output["network_parameters"])

            insert_categories(session, job, parsed_output)

            insert_reference_contours(session, transaction, job, parsed_output)

            filename = request.files['output_file'].filename #CHECK maybe needed
            insert_contours(session, job, parsed_output)

            flash_message = f'Inserted result Job-{job.id} (User: {user.name}).'
        flash(flash_message, 'success')
        response.set_redirect(url_for('results.results'))
    return response.to_json()

@routes_results.route("/results/<job_id>/view", methods = ["GET"])
@login_required
def results_view(job_id):
    """GET route to show the page to add a new result."""
    
    with database_handler.get_session() as session:
            job = database_handler.create_system_time_request(session, models.Job, filters={"id":job_id}, one_result=True)
            categories = database_handler.create_system_time_request(session, models.Category, filters={"job_id":job_id})
            return render_template('results/results-view.html', job=job, categories=categories)

@routes_results.route('/results/<job_id>/download-complete-output', methods=['GET'])
@login_required
def download_complete_output(job_id):
    """Download complete output from ARTwarp run for forward compatability reasons."""
    with database_handler.get_session() as session:
        job = database_handler.create_system_time_request(session, models.Job, filters={"id":job_id}, one_result=True)
        filename = f"Complete Output {job.id}: {job.user.name} ({job.upload_datetime})"
        return utils.download_file(job.complete_output, filename)

@routes_results.route('/results/<job_id>/download-discovery-curve', methods=['GET'])
@login_required
def download_discovery_curve(job_id):
    """Download discovery curve from ARTwarp run."""
    with database_handler.get_session() as session:
        job = database_handler.create_system_time_request(session, models.Job, filters={"id":job_id}, one_result=True)
        filename = f"Discovery Curve {job.id}: {job.user.name} ({job.upload_datetime})"
        return utils.download_file(job.discovery_curve, filename)
    