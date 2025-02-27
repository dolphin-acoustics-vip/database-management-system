
import pytest
from ...app.main import create_app
from ...app.database_handler import db, get_session
from ...app.models import User
from ...app import models
from ... import config
import uuid

@pytest.fixture
def app():
    app = create_app(config.TestingConfig)
    try:
        with app.app_context():
            yield app
    finally:
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def runner(app):
    return app.test_cli_runner()

@pytest.fixture
def db_session():
    session = get_session()
    yield session
    session.rollback()
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
        yield client


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

@pytest.fixture
def species(app, db_session):
    with app.app_context():
        species = []
        for i in range(3):
            s = models.Species()
            # s.id = uuid.uuid4()
            s.set_scientific_name('Test Species{}'.format(i))
            db_session.add(s)
            species.append(s)

            # db_session.flush()
    return species

@pytest.fixture
def species_object(species):
    return species[0]

@pytest.fixture
def species_object1(species):
    return species[1]


@pytest.fixture
def encounters(app, species_object, db_session):
    with app.app_context():
        encounters = []
        for i in range(10):
            encounter = models.Encounter(
                encounter_name='Test Encounter {}'.format(i),
                location='Test Location {}'.format(i),
                species_id=species_object.id,
                project='Test Project {}'.format(i),
                file_timezone='0',
                local_timezone='0'
            )
            db_session.add(encounter)
            encounters.append(encounter)
        db_session.commit()
        return encounters

@pytest.fixture
def encounter_object(encounters):
    return encounters[0]

import datetime
@pytest.fixture
def recordings(app, encounter_object, db_session):
    with app.app_context():
        recordings = []
        start_time_increment = datetime.datetime.now()
        for i in range(10):
            recording = models.Recording(
                start_time=start_time_increment,
                encounter_id=encounter_object.id
            )
            start_time_increment = start_time_increment + datetime.timedelta(minutes=1)
            db_session.add(recording)
            recordings.append(recording)
        db_session.commit()
        return recordings

@pytest.fixture
def recording_object(recordings):
    return recordings[0]


@pytest.fixture
def selections(app, recording_object, db_session):
    with app.app_context():
        selections = []
        for i in range(10):
            selection = models.Selection(
                selection_number=i+1,
                recording_id=recording_object.id
            )
            db_session.add(selection)
            selections.append(selection)
        db_session.commit()
        return selections

@pytest.fixture
def selection_object(selections):
    return selections[0]

@pytest.fixture
def selection_object1(selections):
    return selections[1]

@pytest.fixture
def selection_object2(selections):
    return selections[2]

from unittest.mock import Mock

@pytest.fixture
def mock_request():
    request = Mock()
    request.form = Mock()
    return request

@pytest.fixture
def test_species(app, logged_in_client, db_session):
    with app.app_context():
        species = models.Species()
        species.id = str(uuid.uuid4())
        species.set_scientific_name('Test Species')
        db_session.add(species)
        db_session.commit()

        yield species

@pytest.fixture
def test_encounter(app, test_species, logged_in_client, db_session):
    with app.app_context():
        species_id = test_species.id

        encounter = models.Encounter()
        encounter.set_encounter_name('Test Encounter')
        encounter.set_location('Test Location')
        encounter.set_project('Test Project')
        encounter.set_notes('Test Notes')
        encounter.set_species_id(db_session, species_id)
        encounter.set_latitude('37.7749')
        encounter.set_longitude('-122.4194')
        encounter.set_file_timezone('0')
        encounter.set_local_timezone('0')

        db_session.add(encounter)
        db_session.commit()

        yield encounter