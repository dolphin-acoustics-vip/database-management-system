# Third-party imports
from flask import Blueprint, flash,get_flashed_messages, jsonify, redirect,render_template,request, send_file,session, url_for, send_from_directory
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timedelta
from flask_login import login_required

# Local application imports
from database_handler import Session, require_live_session,exclude_role_1,exclude_role_2,exclude_role_3,exclude_role_4
from models import *
from exception_handler import *
import check_filespace


routes_filespace = Blueprint('filespace', __name__)


@routes_filespace.route('/filespace', methods=['GET'])
@login_required
@exclude_role_2
@exclude_role_3
@exclude_role_4
def filespace():
    return check_filespace.check_filespace()