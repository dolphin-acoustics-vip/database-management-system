# tests/conftest.py

import pytest
from app import create_app
from database_handler import db, get_session
import database_handler
from models import User



@pytest.fixture
def app():
    app = create_app('config.TestingConfig')
    
    with app.app_context():
        yield app
        db.drop_all()  # Clean up database after tests

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def runner(app):
    return app.test_cli_runner()



@pytest.fixture
def db_session(app):
    # Connect to the database
    session = get_session()
    
    yield session  # This provides the session to the test function
    
    # Rollback the transaction after the test
    session.rollback()
    
    # Remove the session
    session.close()

@pytest.fixture
def logged_in_client(app, client, db_session):
    # Create a user in the test database
    with app.app_context():
        user = db_session.query(User).filter_by(login_id='test@testmail.com').first()
        if not user: 
            user = User(login_id='test_system_administrator@testmail.com', password='password', name='System Administrator', role_id=1, is_active=1)
            db_session.add(user)
        db_session.commit()

    # Log the user in
    with app.test_request_context():
        from flask_login import login_user
        login_user(user)

    return client
    

@pytest.fixture
def logged_in_general_client(app, client, db_session):
    # Create a user in the test database
    with app.app_context():
        user = db_session.query(User).filter_by(login_id='test@testmail.com').first()
        if not user:
            user = User(login_id='test_general_user@testmail.com', password='password', name='General User', role_id=2, is_active=1)
            db_session.add(user)
        user.role_id = 3
        db_session.commit()

    # Log the user in
    with app.test_request_context():
        from flask_login import login_user
        login_user(user)

    return client

def test_403_error_page(logged_in_general_client):
    # Simulate a 403 error
    response = logged_in_general_client.get('/admin')

    # Check that the response status code is 403
    assert response.status_code == 403


def test_home_route_logged_out(client):
    response = client.get('/home')
    assert response.status_code == 302

def test_home_route(logged_in_client, db_session):
    response = logged_in_client.get('/home')
    assert response.status_code == 200

def test_home_route_redirect(logged_in_client, db_session):
    response = logged_in_client.get('/')
    assert response.status_code == 302
    assert response.location.startswith('/home')
