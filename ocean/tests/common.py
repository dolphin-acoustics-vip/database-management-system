from sqlalchemy import orm
import sqlalchemy
import pytest
import sqlite3

@pytest.fixture()
def session():
    engine = sqlalchemy.create_engine('sqlite://')
    session = orm.scoped_session(orm.sessionmaker(bind=engine))
    pytest.current_session = session

    yield session

    session.rollback()
    session.remove()