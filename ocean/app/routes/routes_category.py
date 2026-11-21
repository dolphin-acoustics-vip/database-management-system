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
from flask import Blueprint, flash, render_template, redirect, request, session as client_session, url_for, Response
from flask_login import login_required
from datetime import datetime, timedelta

# Local application imports
from .. import database_handler
from .. import models

# Local application imports
from .. import database_handler
from .. import models
from .. import filespace_handler
from .. import exception_handler
from .. import utils
from .. import response_handler
from .. import transaction_handler
from ..logger import logger

routes_category = Blueprint('category', __name__)

@routes_category.route("/category/<category_id>/view", methods = ["GET"])
@login_required
def category_view(category_id):
    """GET route to show all the contours in a category."""
    
    with database_handler.get_session() as session:
        category = database_handler.create_system_time_request(session, models.Category, filters={"id":category_id}, one_result=True)
        contours = database_handler.create_system_time_request(session, models.Contour, filters={"category_id":category_id})
        reference_contour = database_handler.create_system_time_request(session, models.Reference_Contour, filters={"category_id":category_id}, one_result=True)

        return render_template('category/category-view.html', category=category, contours=contours, reference_contour=reference_contour)

@routes_category.route("/category/<category_id>/serve-plot", methods = ["GET"])
@login_required
def serve_reference_contour_plot(category_id):
    """GET route to show reference contour plot."""
    
    with database_handler.get_session() as session:
            filespace_handler.clean_filespace_temp()
            reference_contour = database_handler.create_system_time_request(session, models.Reference_Contour, filters={"category_id":category_id}, one_result=True)
            plot_bytestream = reference_contour.create_temp_plot()
            response = Response(plot_bytestream, mimetype='image/png')
            response.headers['Content-Disposition'] = f'attachment; filename="{category_id}"'
            return response

@routes_category.route("/category/<category_id>/download-reference-contour-csv", methods = ["GET"])
@login_required
def download_reference_contour_file_csv(category_id):
    """GET route to download reference contour as csv."""
    
    with database_handler.get_session() as session:
            reference_contour = database_handler.create_system_time_request(session, models.Reference_Contour, filters={"category_id":category_id}, one_result=True)
            return utils.download_file(reference_contour.contour_file_csv, f"Reference Contour (Category Id: {category_id})", mimetype="text/csv")

@routes_category.route("/category/<category_id>/download-reference-contour-ctr", methods = ["GET"])
@login_required
def download_reference_contour_file_ctr(category_id):
    """GET route to download reference contour as ctr."""
    
    with database_handler.get_session() as session:
            reference_contour = database_handler.create_system_time_request(session, models.Reference_Contour, filters={"category_id":category_id}, one_result=True)
            return utils.download_file(reference_contour.contour_file_ctr, f"Reference Contour (Category Id: {category_id})", mimetype="text/x-ctr")
