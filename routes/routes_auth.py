# Third-party imports
from flask import Blueprint, flash,get_flashed_messages, jsonify, redirect,render_template,request, send_file,session, url_for, send_from_directory
from sqlalchemy.orm import joinedload,sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from flask_login import login_user,login_required, current_user, login_manager, logout_user
from flask import session as client_session
import uuid

# Local application imports
from db import Session, parse_alchemy_error
from models import *
from exception_handler import *

routes_auth = Blueprint('auth', __name__)


@login_required
@routes_auth.route('/profile')
def profile():
    return render_template('authentication/profile.html', user=current_user)

@routes_auth.route('/login', methods=['POST'])
def login_post():
    with Session() as session:
        email = request.form['email']
        password = request.form['password']
        
        user = session.query(User).filter_by(email=email, password=password).first()
        
        if user is None:
            flash('Invalid username or password', 'error')
            return redirect(url_for('auth.login', user=current_user))
        
        login_user(user, remember=False)
                

    return redirect(url_for('home', user=current_user))

@routes_auth.route('/login', methods=['GET'])
def login():
    return render_template('authentication/login.html', user=current_user)


@routes_auth.route('/logout')
def logout():
    logout_user()
    client_session.clear()
    return redirect(url_for('home', user=current_user))