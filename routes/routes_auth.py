# Third-party imports
from flask import app, Blueprint, flash,get_flashed_messages, jsonify, redirect,render_template,request, send_file,session, url_for, send_from_directory
from sqlalchemy.orm import joinedload,sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from flask_login import login_user,login_required, current_user, login_manager, logout_user
from flask import session as client_session
import uuid

# Local application imports
from database_handler import Session,exclude_role_1,exclude_role_2,exclude_role_3,exclude_role_4
from models import *
from exception_handler import *
from logger import logger

routes_auth = Blueprint('auth', __name__)

def login_helper(next_destination: str, is_temporary: bool):
    """
    Helper function for logging in a user. If is_temporary is True, the access code and password are used to log in a temporary user.
    If is_temporary is False, the email and password are used to log in a regular user.

    :param next_destination: The URL to redirect to after successful login
    :param is_temporary: Whether the user is a temporary user
    :return: A redirect to the next destination if the login is successful, or a redirect to the login page if not
    """
    try:
        url_for(next_destination)
    except Exception:
        next_destination = url_for('general.home')
    with Session() as session:
        # Retrieve form information
        if is_temporary:
            login_id = request.form['access_code']
            password = request.form['password']
            user = session.query(User).filter_by(login_id=login_id, password=password, is_temporary=1).first()
        else:
            email = request.form['email']
            password = request.form['password']
            user = session.query(User).filter_by(login_id=email, password=password, is_temporary=0).first()
        # Check for user validity
        if user:
            if not user.is_active:
                flash('Your account has been deactivated. Please contact your administrator.', 'error')
                return redirect(url_for('auth.login' if not is_temporary else 'auth.access_code_login'))
            days_until_expiry = (user.expiry - datetime.now().date()).days
            if user.expiry < datetime.now().date():
                flash('Your account has expired. Please contact your administrator.', 'error')
                return redirect(url_for('auth.login' if not is_temporary else 'auth.access_code_login'))
            elif days_until_expiry <= (7 if not is_temporary else 30):
                flash(f'Your account will be deactivated in {days_until_expiry} days. Please contact your administrator to prevent this.', 'warning')
            # Login user
            login_user(user, remember=False)
            logger.info(f'{"Temporary " if is_temporary else ""}User {user.id} logged in')
            return redirect(next_destination)
        else:
            flash('Invalid username or password' if not is_temporary else 'Invalid access code or password', 'error')
            return redirect(url_for('auth.login' if not is_temporary else 'auth.access_code_login'))

@routes_auth.route('/login', methods=['GET'])
def login():
    next_destination = request.args.get('next')
    return render_template('authentication/login.html', next_destination=next_destination)

@routes_auth.route('/login', methods=['POST'])
def login_post():
    next_destination = request.form.get('next_destination')
    return login_helper(next_destination, False)

@routes_auth.route('/login-temporary', methods=['POST'])
def login_temporary_post():
    next_destination = request.form.get('next_destination')
    return login_helper(next_destination, True)

@routes_auth.route('/access-code-login', methods=['GET'])
def access_code_login():
    next_destination = request.args.get('next')
    return render_template('authentication/login-with-access-code.html', next_destination=next_destination)

@routes_auth.route('/logout')
def logout():
    logout_user()
    client_session.clear()
    return redirect(url_for('general.home'))