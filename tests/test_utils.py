import pytest
from main import create_app
from database_handler import db, get_session
from models import User
import utils
from unittest.mock import Mock
from flask import *



def test_home_route(logged_in_client, db_session):
    response = logged_in_client.get('/home')
    assert response.status_code == 200

def test_home_route_redirect(logged_in_client, db_session):
    response = logged_in_client.get('/')
    assert response.status_code == 302
    assert response.location.startswith('/home')



def test_valid_form_data(mock_request):
    mock_request.form.to_dict.return_value = {'name': 'John', 'age': '30'}
    schema = {'name': str, 'age': int}
    data = utils.get_form_data(mock_request, schema)
    assert data == {'name': 'John', 'age': 30}

def test_missing_key(mock_request):
    mock_request.form.to_dict.return_value = {'name': 'John'}
    schema = {'name': str, 'age': int}
    with pytest.raises(ValueError) as e:
        utils.get_form_data(mock_request, schema)
    assert type(e.value) == ValueError

def test_invalid_data_type(mock_request):
    mock_request.form.to_dict.return_value = {'name': 'John', 'age': 'abc'}
    schema = {'name': str, 'age': int}
    with pytest.raises(ValueError) as e:
        utils.get_form_data(mock_request, schema)
    assert type(e.value) == ValueError

def test_invalid_data_type2(mock_request):
    mock_request.form.to_dict.return_value = {'name': 'John', 'age': '1.32'}
    schema = {'name': str, 'age': int}
    with pytest.raises(ValueError) as e:
        utils.get_form_data(mock_request, schema)
    assert type(e.value) == ValueError