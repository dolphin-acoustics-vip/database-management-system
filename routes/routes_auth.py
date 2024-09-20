# Third-party imports
from flask import Blueprint, flash,get_flashed_messages, jsonify, redirect,render_template,request, send_file,session, url_for, send_from_directory
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

@routes_auth.route('/access-code-login', methods=['GET'])
def access_code_login():
    return render_template('authentication/login-with-access-code.html')

@routes_auth.route('/access-code-login', methods=['POST'])
def access_code_login_post():
    return render_template('home.html')

@routes_auth.route('/login', methods=['POST'])
def login_post():
    with Session() as session:
        email = request.form['email']
        password = request.form['password']
        user = session.query(User).filter_by(login_id=email, password=password, is_temporary=0).first()
        if user:
            if not user.is_active:
                flash('Your account has been deactivated. Please contact your administrator.', 'error')
                return redirect(url_for('auth.login'))
            days_until_expiry = (user.expiry - datetime.now().date()).days
            if user.expiry < datetime.now().date():
                flash('Your account has expired. Please contact your administrator.', 'error')
                return redirect(url_for('auth.login'))
            elif days_until_expiry <= 7:
                flash(f'Your account will be deactivated in {days_until_expiry} days. Please contact your administrator to prevent this.', 'warning')
            if user is None:
                flash('Invalid username or password', 'error')
                return redirect(url_for('auth.login'))
            login_user(user, remember=False)
            logger.info(f'User {user.id} logged in')
            return redirect(url_for('general.home'))
        else:
            flash('Invalid username or password', 'error')
            return redirect(url_for('auth.login'))

@routes_auth.route('/login-temporary', methods=['POST'])
def login_temporary_post():
    with Session() as session:
        login_id = request.form['access_code']
        password = request.form['password']
        user = session.query(User).filter_by(login_id=login_id, password=password, is_temporary=1).first()
        if user:
            if not user.is_active:
                flash('Your account has been deactivated. Please contact your administrator.', 'error')
                return redirect(url_for('auth.access_code_login'))
            days_until_expiry = (user.expiry - datetime.now().date()).days
            if user.expiry < datetime.now().date():
                flash('Your account has expired. Please contact your administrator.', 'error')
                return redirect(url_for('auth.access_code_login'))
            elif days_until_expiry <= 30:
                flash(f'Your account will be deactivated in {days_until_expiry} days. Please contact your administrator to prevent this.', 'warning')
            if user is None:
                flash('Invalid login ID or password', 'error')
                return redirect(url_for('auth.access_code_login'))
            login_user(user, remember=False)
            logger.info(f'Temprary user {user.id} logged in')
            return redirect(url_for('general.home'))
        else:
            flash('Invalid access code or password', 'error')
            return redirect(url_for('auth.access_code_login'))

@routes_auth.route('/login', methods=['GET'])
def login():
    return render_template('authentication/login.html')

@routes_auth.route('/logout')
def logout():
    logout_user()
    client_session.clear()
    return redirect(url_for('general.home'))