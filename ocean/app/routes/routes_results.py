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
from flask_login import login_required
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

@routes_results.route('/results/insert', methods=['POST'])
@login_required
@database_handler.exclude_role_3
@database_handler.exclude_role_4
@database_handler.require_live_session
def results_insert():
    with response_handler.json_response_context() as response:
        with transaction_handler.atomic() as session:
            job = models.Job()
            job.insert(request.form)
            session.add(job)
            flash_message = f'Inserted result {job.unique_name}.'
        flash(flash_message, 'success')
        response.set_redirect(url_for('results.results'))
    return response.to_json()

@routes_results.route("/results/<job_id>/view", methods = ["GET"])
@login_required
def results_view(job_id):
    """GET route to show the page to add a new result."""
    
    with database_handler.get_session() as session:
            job = database_handler.create_system_time_request(session, models.Job, {"id":job_id})[0]

            return render_template('results/results-view.html', job=job)
    