# Standard library imports
import re

# Third-party imports
from flask import Blueprint, flash,get_flashed_messages, jsonify, redirect,render_template,request, send_file,session, url_for, send_from_directory
from sqlalchemy.orm import joinedload,sessionmaker
from sqlalchemy.exc import SQLAlchemyError

# Location application imports
from db import FILE_SPACE_PATH, Session, GOOGLE_API_KEY, db, parse_alchemy_error,exclude_role_1,exclude_role_2,exclude_role_3,exclude_role_4
from models import *

routes_contour = Blueprint('contour', __name__)
