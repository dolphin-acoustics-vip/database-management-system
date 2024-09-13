import pytest
from main import create_app
from database_handler import db, get_session
from models import User
import utils
from unittest.mock import Mock
from flask import *

import pytest
from datetime import datetime
from uuid import UUID, uuid4

# Test validate_datetime function
def test_validate_datetime_valid_string():
    date_string = "2022-01-01T12:00:00"
    result = utils.validate_datetime(date_string)
    assert isinstance(result, datetime)
    assert result.year == 2022
    assert result.month == 1
    assert result.day == 1
    assert result.hour == 12
    assert result.minute == 0
    assert result.second == 0

def test_validate_datetime_valid_string_without_seconds():
    date_string = "2022-01-01T12:00"
    result = utils.validate_datetime(date_string)
    assert isinstance(result, datetime)
    assert result.year == 2022
    assert result.month == 1
    assert result.day == 1
    assert result.hour == 12
    assert result.minute == 0
    assert result.second == 0

def test_validate_datetime_invalid_string():
    date_string = "invalid-date"
    with pytest.raises(Exception):
        utils.validate_datetime(date_string)

def test_validate_datetime_valid_datetime():
    date = datetime(2022, 1, 1, 12, 0, 0)
    result = utils.validate_datetime(date)
    assert result == date

def test_validate_datetime_invalid_datetime():
    with pytest.raises(Exception):
        utils.validate_datetime("not-a-date")

# Test validate_latitude function
def test_validate_latitude_valid_float():
    latitude = 45.0
    result = utils.validate_latitude(latitude)
    assert result == latitude

def test_validate_latitude_valid_string():
    latitude = "45.0"
    result = utils.validate_latitude(latitude)
    assert result == 45.0

def test_validate_latitude_invalid_string():
    latitude = "invalid-latitude"
    with pytest.raises(Exception):
        utils.validate_latitude(latitude)

def test_validate_latitude_out_of_range():
    latitude = 100.0
    with pytest.raises(Exception):
        utils.validate_latitude(latitude)

# Test validate_longitude function
def test_validate_longitude_valid_float():
    longitude = 45.0
    result = utils.validate_longitude(longitude)
    assert result == longitude

def test_validate_longitude_valid_string():
    longitude = "45.0"
    result = utils.validate_longitude(longitude)
    assert result == 45.0

def test_validate_longitude_invalid_string():
    longitude = "invalid-longitude"
    with pytest.raises(Exception):
        utils.validate_longitude(longitude)

def test_validate_longitude_out_of_range():
    longitude = 200.0
    with pytest.raises(Exception):
        utils.validate_longitude(longitude)

# Test validate_float function
def test_validate_float_valid_float():
    float_value = 45.0
    result = utils.validate_float(float_value)
    assert result == float_value

def test_validate_float_valid_string():
    float_value = "45.0"
    result = utils.validate_float(float_value)
    assert result == 45.0

def test_validate_float_invalid_string():
    float_value = "invalid-float"
    with pytest.raises(Exception):
        utils.validate_float(float_value)

# Test validate_id function
def test_validate_id_valid_uuid():
    uuid_value = uuid4()
    result = utils.validate_id(uuid_value)
    assert result == str(uuid_value)

def test_validate_id_valid_string():
    uuid_value = str(uuid4())
    result = utils.validate_id(uuid_value)
    assert result == uuid_value

def test_validate_id_invalid_string():
    uuid_value = "invalid-uuid"
    with pytest.raises(Exception):
        utils.validate_id(uuid_value)

# Test validate_timezone function
def test_validate_timezone_valid_int():
    timezone = 0
    result = utils.validate_timezone(timezone)
    assert result == timezone

def test_validate_timezone_valid_string():
    timezone = "0"
    result = utils.validate_timezone(timezone)
    assert result == 0

def test_validate_timezone_invalid_string():
    timezone = "invalid-timezone"
    with pytest.raises(Exception):
        utils.validate_timezone(timezone)

def test_validate_timezone_out_of_range():
    timezone = 1000
    with pytest.raises(Exception):
        utils.validate_timezone(timezone)

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

import pandas as pd
empty_file_error_message = "File is empty".lower()

def test_extract_to_dataframe_csv():
    path = "tests/resources/utils/dataframe-3-rows.csv"
    df = utils.extract_to_dataframe(path)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 3

def test_extract_to_dataframe_csv_empty():
    path = "tests/resources/utils/dataframe-empty.csv"
    with pytest.raises(ValueError) as e:
        df = utils.extract_to_dataframe(path)
    assert str(e.value).lower() == empty_file_error_message


def test_extract_to_dataframe_txt():
    path = "tests/resources/utils/dataframe-3-rows.txt"
    df = utils.extract_to_dataframe(path)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 3

def test_extract_to_dataframe_txt_empty():
    path = "tests/resources/utils/dataframe-empty.txt"
    with pytest.raises(ValueError) as e:
        df = utils.extract_to_dataframe(path)
    assert str(e.value).lower() == empty_file_error_message    

def test_extract_to_dataframe_xlsx_empty():
    path = "tests/resources/utils/dataframe-empty.xlsx"
    with pytest.raises(ValueError) as e:
        df = utils.extract_to_dataframe(path)
    assert str(e.value).lower() == empty_file_error_message
    

def test_extract_to_dataframe_xlsx():
    path = "tests/resources/utils/dataframe-3-rows.xlsx"
    df = utils.extract_to_dataframe(path)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 3


def test_extract_to_dataframe_nonexistent_file():
    path = "tests/resources/utils/nonexistent-file.txt"
    with pytest.raises(FileNotFoundError) as e:
        df = utils.extract_to_dataframe(path)

