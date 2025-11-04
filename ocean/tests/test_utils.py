import os
import pytest
from unittest.mock import Mock
from flask import *

from ..app import exception_handler, utils, models
from ..app.interfaces import imodels
from . import common, factories

from datetime import datetime
from uuid import UUID, uuid4

@pytest.mark.parametrize("value, expected", [
    ("True", True),
    ("False", False),
    ("true", True),
    ("false", False),
    (True, True),
    (False, False),
    (1, True),
    (0, False),
    ("1", True),
    ("0", False),
])
def test_validate_boolean(value, expected):
    assert utils.validate_boolean(value, "test", allow_none = False) == expected

@pytest.mark.parametrize("value", common.EMPTY_CHARACTERS)
def test_validate_boolean_none(value):
    assert utils.validate_boolean(value, "test", allow_none = True) == None
    with pytest.raises(exception_handler.WarningException):
        utils.validate_boolean(value, "test", allow_none = False)

@pytest.mark.parametrize("value", [2,"2",-1,"-1","not-a-boolean"])
def test_validate_boolean_invalid(value):
    with pytest.raises(exception_handler.ValidationError):
        utils.validate_boolean(value, "test", allow_none = False)
    with pytest.raises(exception_handler.ValidationError):
        utils.validate_boolean(value, "test", allow_none = True)

# # Test validate_datetime function
# def test_validate_datetime_valid_string():
#     date_string = "2022-01-01T12:00:00"
#     result = utils.validate_datetime(date_string)
#     assert isinstance(result, datetime)
#     assert result.year == 2022
#     assert result.month == 1
#     assert result.day == 1
#     assert result.hour == 12
#     assert result.minute == 0
#     assert result.second == 0

# def test_validate_datetime_valid_string_without_seconds():
#     date_string = "2022-01-01T12:00"
#     result = utils.validate_datetime(date_string)
#     assert isinstance(result, datetime)
#     assert result.year == 2022
#     assert result.month == 1
#     assert result.day == 1
#     assert result.hour == 12
#     assert result.minute == 0
#     assert result.second == 0

# def test_validate_datetime_invalid_string():
#     date_string = "invalid-date"
#     with pytest.raises(Exception):
#         utils.validate_datetime(date_string)

# def test_validate_datetime_valid_datetime():
#     date = datetime(2022, 1, 1, 12, 0, 0)
#     result = utils.validate_datetime(date)
#     assert result == date

# def test_validate_datetime_invalid_datetime():
#     with pytest.raises(Exception):
#         utils.validate_datetime("not-a-date")

# Test validate_latitude function

@pytest.mark.parametrize("value, expected", [
    (45, 45),
    (90, 90),
    ("50", 50),
    (0, 0),
    ("0", 0),
    (-90, -90),
    ("-90", -90),
    (45.1, 45.1),
    (-180, -180),
    (180, 180)
])
def test_validate_longitude_valid_float(value, expected):
    assert utils.validate_longitude(value, "test", allow_none = False) == expected

@pytest.mark.parametrize("value", [-181, 181, "-181", "181", 180.5, "not-longitude"])
def test_validate_longitude_invalid(value):
    with pytest.raises(exception_handler.ValidationError):
        utils.validate_longitude(value, "test", allow_none = False)
    with pytest.raises(exception_handler.ValidationError):
        utils.validate_longitude(value, "test", allow_none = True)

@pytest.mark.parametrize("value", common.EMPTY_CHARACTERS)
def test_validate_longitude_none(value):
    assert utils.validate_longitude(value, "test", allow_none = True) == None
    with pytest.raises(exception_handler.WarningException):
        utils.validate_longitude(value, "test", allow_none = False)


@pytest.mark.parametrize("value, expected", [
    (45, 45),
    (90, 90),
    ("50", 50),
    (0, 0),
    ("0", 0),
    (-90, -90),
    ("-90", -90),
    (45.1, 45.1),
])
def test_validate_latitude_valid_float(value, expected):
    assert utils.validate_latitude(value, "test", allow_none = False) == expected

@pytest.mark.parametrize("value", [-91, 91, "-91", "91", 90.5, "not-latitude"])
def test_validate_latitude_invalid(value):
    with pytest.raises(exception_handler.ValidationError):
        utils.validate_latitude(value, "test", allow_none = False)
    with pytest.raises(exception_handler.ValidationError):
        utils.validate_latitude(value, "test", allow_none = True)

@pytest.mark.parametrize("value", common.EMPTY_CHARACTERS)
def test_validate_latitude_none(value):
    assert utils.validate_latitude(value, "test", allow_none = True) == None
    with pytest.raises(exception_handler.WarningException):
        utils.validate_latitude(value, "test", allow_none = False)


@pytest.mark.parametrize("value, expected", [
    ("Test string", "Test string"),
    (" Test string", "Test string"),
    (" Test string ", "Test string"),
    ("Test string ", "Test string")
])
def test_validate_string(value, expected):
    assert utils.validate_string(value, "test", allow_none = False) == expected
    assert utils.validate_string(value, "test", allow_none = True) == expected

@pytest.mark.parametrize("value", common.EMPTY_CHARACTERS)
def test_validate_string_none(value):
    assert utils.validate_string(value, field="test", allow_none = True) == None
    with pytest.raises(exception_handler.ValidationError):
        utils.validate_string(value, field="test", allow_none = False)

@pytest.mark.parametrize("value", [1, 6.7])
def test_validate_string_invalid(value):
    with pytest.raises(exception_handler.ValidationError):
        utils.validate_string(value, field="test")



@pytest.mark.parametrize("value, expected", [
    (1, 1.0),
    (1.0, 1.0),
    ("1.0", 1.0),
    ("1", 1.0),
    ("-9.315", -9.315),
    (0, 0.0),
    (0.05, 0.05),
    ("0", 0.0),
    (" 1", 1.0),
    (" 325.431 \n", 325.431)
])
def test_validate_float(value, expected):
    assert utils.validate_float(value, "test", allow_none = False) == expected

@pytest.mark.parametrize("value", ["-1.04d2", "not-a-float"])
def test_validate_float_invalid(value):
    with pytest.raises(exception_handler.ValidationError):
        utils.validate_float(value, "test", allow_none = False)
    with pytest.raises(exception_handler.ValidationError):
        utils.validate_float(value, "test", allow_none = True)

@pytest.mark.parametrize("value", common.EMPTY_CHARACTERS)
def test_validate_float_none(value):
    assert utils.validate_float(value, "test", allow_none = True) == None
    with pytest.raises(exception_handler.WarningException):
        utils.validate_float(value, "test", allow_none = False)


@pytest.mark.parametrize("value, expected", [
    (1, 1),
    (1.0, 1),
    ("1.0", 1),
    ("1", 1),
    ("-9.315", -9),
    (0, 0),
    (0.05, 0),
    ("0", 0),
    (" 1", 1),
    (" 325.431 \n", 325)
])
def test_validate_int(value, expected):
    assert utils.validate_int(value, "test", allow_none = False) == expected

@pytest.mark.parametrize("value", ["-1d", "not-an-int"])
def test_validate_int_invalid(value):
    with pytest.raises(exception_handler.ValidationError):
        utils.validate_int(value, "test", allow_none = False)
    with pytest.raises(exception_handler.ValidationError):
        utils.validate_int(value, "test", allow_none = True)

@pytest.mark.parametrize("value", common.EMPTY_CHARACTERS)
def test_validate_int_none(value):
    assert utils.validate_int(value, "test", allow_none = True) == None
    with pytest.raises(exception_handler.WarningException):
        utils.validate_int(value, "test", allow_none = False)

def test_validate_id_valid_uuid():
    uuid_value = uuid4()
    result = utils.validate_id(uuid_value, field="test")
    assert result == uuid_value

def test_validate_id_valid_string():
    uuid_value = uuid4()
    result = utils.validate_id(str(uuid_value), field="test")
    assert result == uuid_value

def test_validate_id_invalid_string():
    uuid_value = "invalid-uuid"
    with pytest.raises(Exception):
        utils.validate_id(uuid_value, field="test")

@pytest.mark.parametrize("value", common.EMPTY_CHARACTERS)
def test_validate_id_none(value):
    assert utils.validate_id(value, "test", allow_none = True) == None
    with pytest.raises(exception_handler.WarningException):
        utils.validate_id(value, "test", allow_none = False)

def test_validate_type():
    assert utils.validate_type(models.File(), models.File, "test", allow_none = False)

def test_validate_type_subclass():
    # Note File is a subclass of IFile
    assert utils.validate_type(models.File(), imodels.IFile, "test", allow_none = False)

@pytest.mark.parametrize("value", ["", None])
def test_validate_type_none(value):
    assert utils.validate_type(value, int, "test", allow_none = True) == None
    with pytest.raises(exception_handler.WarningException):
        utils.validate_type(value, int, "test", allow_none = False)

@pytest.mark.parametrize("value, expected", [
    (-720, -720),
    (-100, -100),
    (-260.6, -260),
    (0, 0),
    (0.0, 0),
    ("0", 0),
    ("0.0", 0),
    (0.5, 0),
    (100, 100),
    ("840", 840),
    ("-720", -720),
    ("-100", -100),
    ("-260.6", -260),
    ("0", 0),
    ("0.5", 0),
    ("100", 100),
    ("840", 840),
])
def test_validate_timezone(value, expected):
    assert utils.validate_timezone(value, field = "test") == expected

@pytest.mark.parametrize("value", ["not-a-timezone", "720d", "0f"])
def test_validate_timezone_invalid_string(value):
    with pytest.raises(Exception):
        utils.validate_timezone(value, field = "test")

@pytest.mark.parametrize("value", [841, -721, 100000, -100000])
def test_validate_timezone_out_of_range(value):
    with pytest.raises(Exception):
        utils.validate_timezone(value, field = "test")

@pytest.mark.parametrize("invalid_char", common.INVALID_CHARACTERS)
def test_secure_filename(invalid_char):
    assert utils.secure_fname(f"Test{invalid_char}File") == "Test_File"
    assert utils.secure_fname(f" Test{invalid_char}File") == "Test_File"
    assert utils.secure_fname(f"Test{invalid_char}File ") == "Test_File"
    assert utils.secure_fname(f" Test{invalid_char}File ") == "Test_File"

@pytest.mark.parametrize("value", common.EMPTY_CHARACTERS)
def test_secure_filename_none(value):
    with pytest.raises(exception_handler.CriticalException):
        assert utils.secure_fname(value)

@pytest.mark.parametrize("year, month, day, hour, minute, second, expected", [
    (2024, 8, 10, 20, 44, 33, "20240810T204433"),
    (2024, 8, 4, 1, 6, 2, "20240804T010602"),
])
def test_secure_datename(year, month, day, hour, minute, second, expected):
    d = datetime(year, month, day, hour, minute, second)
    assert utils.secure_datename(d) == expected

def test_secure_datename_wrong_type():
    with pytest.raises(exception_handler.CriticalException):
        utils.secure_datename(models.File())

@pytest.mark.parametrize("value", common.EMPTY_CHARACTERS)
def test_secure_datename_none(value):
    with pytest.raises(exception_handler.CriticalException):
        utils.secure_datename(value)

# # Test validate_float function
# def test_validate_float_valid_float():
#     float_value = 45.0
#     result = utils.validate_float(float_value)
#     assert result == float_value

# def test_validate_float_valid_string():
#     float_value = "45.0"
#     result = utils.validate_float(float_value)
#     assert result == 45.0

# def test_validate_float_invalid_string():
#     float_value = "invalid-float"
#     with pytest.raises(Exception):
#         utils.validate_float(float_value)


# def test_valid_form_data(mock_request):
#     mock_request.form.to_dict.return_value = {'name': 'John', 'age': '30'}
#     schema = {'name': str, 'age': int}
#     data = utils.get_form_data(mock_request, schema)
#     assert data == {'name': 'John', 'age': 30}

# def test_missing_key(mock_request):
#     mock_request.form.to_dict.return_value = {'name': 'John'}
#     schema = {'name': str, 'age': int}
#     with pytest.raises(ValueError) as e:
#         utils.get_form_data(mock_request, schema)
#     assert type(e.value) == ValueError

# def test_invalid_data_type(mock_request):
#     mock_request.form.to_dict.return_value = {'name': 'John', 'age': 'abc'}
#     schema = {'name': str, 'age': int}
#     with pytest.raises(ValueError) as e:
#         utils.get_form_data(mock_request, schema)
#     assert type(e.value) == ValueError

# def test_invalid_data_type2(mock_request):
#     mock_request.form.to_dict.return_value = {'name': 'John', 'age': '1.32'}
#     schema = {'name': str, 'age': int}
#     with pytest.raises(ValueError) as e:
#         utils.get_form_data(mock_request, schema)
#     assert type(e.value) == ValueError

import pandas as pd
empty_file_error_message = "File is empty".lower()

BASE_DIR = "ocean/tests/resources/utils"


def test_extract_to_dataframe_csv():
    path = os.path.join(BASE_DIR,"dataframe-3-rows.csv")
    df = utils.extract_to_dataframe(path)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 3

def test_extract_to_dataframe_csv_empty():
    path = os.path.join(BASE_DIR,"dataframe-empty.csv")
    with pytest.raises(exception_handler.WarningException) as e:
        df = utils.extract_to_dataframe(path)
    assert str(e.value).lower() == empty_file_error_message


def test_extract_to_dataframe_txt():
    path = os.path.join(BASE_DIR,"dataframe-3-rows.txt")
    df = utils.extract_to_dataframe(path)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 3

def test_extract_to_dataframe_txt_empty():
    path = os.path.join(BASE_DIR,"dataframe-empty.txt")
    with pytest.raises(exception_handler.WarningException) as e:
        df = utils.extract_to_dataframe(path)
    assert str(e.value).lower() == empty_file_error_message    

def test_extract_to_dataframe_xlsx_empty():
    path = os.path.join(BASE_DIR,"dataframe-empty.xlsx")
    with pytest.raises(exception_handler.WarningException) as e:
        df = utils.extract_to_dataframe(path)
    assert str(e.value).lower() == empty_file_error_message
    

def test_extract_to_dataframe_xlsx():
    path = os.path.join(BASE_DIR,"dataframe-3-rows.xlsx")
    df = utils.extract_to_dataframe(path)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 3


def test_extract_to_dataframe_nonexistent_file():
    path = os.path.join(BASE_DIR,"nonexistent-file.txt")
    with pytest.raises(FileNotFoundError) as e:
        df = utils.extract_to_dataframe(path)

@pytest.mark.parametrize("value, expected", [
    ("sel_01_HICEAS020814115547.wav",datetime(2002,8,14,11,55,47)),
    ("sel_01_HICEAS020814_115547.wav",datetime(2002,8,14,11,55,47)),
    ("sel_01_HICEAS020814-115547.wav",datetime(2002,8,14,11,55,47)),
    ("sel_01_HICEAS020814T115547.wav",datetime(2002,8,14,11,55,47)),
    ("sel_01_HICEAS20020814115547.wav",datetime(2002,8,14,11,55,47)),
    ("sel_01_HICEAS20020814_115547.wav",datetime(2002,8,14,11,55,47)),
    ("sel_01_HICEAS20020814-115547.wav",datetime(2002,8,14,11,55,47)),
    ("sel_01_HICEAS20020814T115547.wav",datetime(2002,8,14,11,55,47)),
])
def test_parse_date(value, expected):
    from . import common
    assert common.equate_timestamps(utils.parse_date(value), expected)
    
@pytest.mark.parametrize("value", common.EMPTY_CHARACTERS)
def test_parse_date_none(value):
    assert utils.parse_date(value) == None

@pytest.mark.parametrize("value", ["No date"])
def test_parse_date_not_found(value):
    assert utils.parse_date(value) == None

@pytest.mark.parametrize("form, schema, expected", [
    ({"arg1":"val1", "arg2": "val2"}, {"arg1": True, "arg2": True}, {"arg1":"val1", "arg2": "val2"}),
    ({"arg1":"val1", "arg2": "val2"}, {"arg1": False, "arg2": False}, {"arg1":"val1", "arg2": "val2"}),
    ({"arg2": "val2"}, {"arg1": False, "arg2": True}, {"arg2": "val2"}),
    ({"arg1":"val1"}, {"arg1": True, "arg2": False}, {"arg1":"val1"}),
    ({"arg1":"val1", "arg2": "val2", "arg3": "val3"}, {"arg1": True, "arg2": True}, {"arg1":"val1", "arg2": "val2"}),
])
def test_parse_form(form, schema, expected):
    assert utils.parse_form(form, schema) == expected

@pytest.mark.parametrize("form, schema", [
    ({"arg1":"val1"}, {"arg1": True, "arg2": True}),
    ({"arg2": "val2"}, {"arg1": True, "arg2": False}),
])
def test_parse_form_invalid(form, schema):
    with pytest.raises(AttributeError):
        utils.parse_form(form, schema)

@pytest.mark.parametrize("source, selnum", [
    ("recording_sel-2_data.csv", "2"),
    ("recording_sel_3_data.csv", "3"),
    ("recording_sel_03_data.csv", "3"),
    ("recording_sel_0020_data.csv", "20"),
    ("recording_sel_data.csv", None),
])
def test_selection_regex_hyphen(source, selnum):
    extracted_selnum = utils.extract_selection_number(source)
    assert extracted_selnum == selnum
