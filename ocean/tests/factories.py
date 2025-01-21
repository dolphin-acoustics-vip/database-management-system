import factory
import pytest
from ..app import models
from . import common
import uuid
from sqlalchemy import Column, Integer, Unicode, create_engine
from sqlalchemy.orm import declarative_base, scoped_session, sessionmaker
from sqlalchemy import text

database_name = f"ocean_test_{uuid.uuid4().hex}"

engine = create_engine(f"mariadb+pymysql://root:test123@localhost/ocean_test")
Session = scoped_session(sessionmaker(bind=engine))
Base = declarative_base()

def clear_database(connection):
    connection.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
    tables = connection.execute(text("SHOW TABLES"))
    for table in tables:
        connection.execute(text(f"DROP TABLE {table[0]}"))
    connection.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
    
@pytest.fixture
def session():
    connection = engine.connect()
    clear_database(connection)
    models.Species.metadata.create_all(bind=engine)
    yield Session
    Session.remove()
    clear_database(connection)
    connection.close()

# Base.metadata.create_all(engine)

class FileFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = models.File
        sqlalchemy_session = Session
    
    # id = factory.LazyAttribute(lambda x: uuid.uuid4().hex)
    # updated_by_id = None

class RecordingPlatformFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = models.RecordingPlatform
        sqlalchemy_session = Session
    id = factory.LazyAttribute(lambda x: uuid.uuid4().hex)
    name = factory.Faker('name')
    updated_by_id = None

class DataSourceFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = models.DataSource
        sqlalchemy_session = Session

    id = factory.LazyAttribute(lambda x: uuid.uuid4().hex)
    name = factory.Faker('name')
    email1 = factory.Faker('email')
    email2 = factory.Faker('email')
    address = factory.Faker('address')
    notes = factory.Faker('text')
    updated_by_id = None

class SpeciesFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = models.Species
        sqlalchemy_session = Session
    id = factory.LazyAttribute(lambda x: uuid.uuid4().hex)
    scientific_name = factory.Faker('name')
    genus_name = factory.Faker('name')
    common_name = factory.Faker('name')
    updated_by_id = None

class EncounterFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = models.Encounter
        sqlalchemy_session = Session
    id = factory.LazyAttribute(lambda x: uuid.uuid4().hex)
    encounter_name = factory.Faker('name')
    location = factory.Faker('city')
    project = factory.Faker('company')
    species = SpeciesFactory.create()
    species_id = species.id
    updated_by_id = None

class RecordingFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = models.Recording
        sqlalchemy_session = Session
    id = factory.LazyAttribute(lambda x: uuid.uuid4().hex)
    start_time = factory.Faker('date_time')
    encounter = factory.SubFactory(EncounterFactory)
    status = "Unassigned"
    updated_by_id = None

class SelectionFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = models.Selection
        sqlalchemy_session = Session
    id = factory.LazyAttribute(lambda x: uuid.uuid4().hex)
    selection_number = factory.Faker('random_int')
    recording = factory.SubFactory(RecordingFactory)
    updated_by_id = None
    
class RoleFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = models.Role
        sqlalchemy_session = Session
    
    id = factory.Faker('random_int')
    name = factory.Faker('name')
    
class UserFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = models.User
        sqlalchemy_session = Session
    
    id = factory.LazyAttribute(lambda x: uuid.uuid4().hex)
    login_id = factory.Faker('email')
    name = factory.Faker('name')
    is_active = True
    
class AssignmentFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = models.Assignment
        sqlalchemy_session = Session
    
    recording = EncounterFactory.create()
    user = UserFactory.create()
    completed_flag = False
    
from ..app import contour_statistics
class ContourFileHandlerFactory(factory.Factory):
    class Meta:
        model = contour_statistics.ContourFileHandler
